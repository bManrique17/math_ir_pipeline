"""Extract formula descriptors from silver posts and write them back.

Reads rows from {silver_schema}.post_arqmath where normalized_text_placeholders_formula_id
is present and formula_descriptors is still NULL. In that column, each formula is
inlined as a bracketed raw formula id, e.g. "...the space [336] of continuous...",
where 336 is formula_arqmath.id. Calls an LLM (via Ollama) once per row to extract
formula descriptors (raw_formula_id -> list[str] mappings, keyed by that same id as
a string, e.g. {"336": ["the space of continuous functions"]}), and writes the
result back into that row's formula_descriptors column (JSONB).

Rows whose text has no bracketed formula placeholder at all are never sent to the
LLM; formula_descriptors is explicitly set to {} (empty object) for them instead of
being left untouched, so stale values (e.g. from a previous run, surfaced via
overwrite=True) don't linger. This also keeps NULL meaning strictly "not yet
processed" while {} means "processed, no formulas found".

Rows are only ever selected when formula_descriptors IS NULL by default, so this
step is resumable: re-running it after a crash or interruption picks up where it
left off, and rows whose LLM call failed are left untouched (and logged) so they
get retried on the next run.

Promoted from the standalone prototype at
DEBUG/extract_formula_descriptors/extract_descriptors_standalone.py.
"""

import json
import logging
import re
import socket
import subprocess
import time

import ollama
import requests
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tqdm import tqdm

logger = logging.getLogger(__name__)

POST_TABLE = "post_arqmath"
ID_COLUMN = "silver_id"
TEXT_COLUMN = "normalized_text_placeholders_formula_id"
OUTPUT_COLUMN = "formula_descriptors"

SYSTEM_PROMPT = (
    "You are a mathematical expert. You can link formulas with their description "
    "appearing in a paragraph. Formulas appear as bracketed numeric placeholders, "
    "e.g. [336], [42], [7891], where the number is an arbitrary formula id.\n\n"
    "Your task is to extract pairs like (formula, description) from the given paragraph. "
    "Each pair must be on its own line. If a formula has multiple descriptions, "
    "repeat the formula in separate pairs. Output only the pairs, one per line.\n\n"
    "Example 1:\n"
    "Input: Given [10] that belongs to [11], demonstrate that [12] is always positive.\n"
    "Output:\n"
    "([10], belongs to [11])\n"
    "([12], always positive)\n\n"
    "Example 2:\n"
    "Input: The velocity [20] is defined as [21] where [22] is the displacement.\n"
    "Output:\n"
    "([20], defined as [21])\n"
    "([22], the displacement)\n\n"
    "Rules:\n"
    "Only use text present in the paragraph.\n"
    "Only use bracketed placeholder ids present in the paragraph, exactly as written (e.g. [336]).\n"
    "If a formula has multiple descriptions, repeat it in separate pairs.\n"
    "Output only the pairs, one per line. Nothing else.\n"
)

USER_TEMPLATE = "What are the pairs for the following paragraph?:\n{passage}\n"

_FORMULA_RE = re.compile(r"\[(\d+)\]")


class _Pair(BaseModel):
    formula: str
    definitions: list[str]


class _Pairs(BaseModel):
    pairs: list[_Pair]


# ---------------------------------------------------------------------------
# Ollama server management
# ---------------------------------------------------------------------------


def _start_ollama(gpu_id: int, port: int) -> subprocess.Popen:
    import os

    env = {k: v for k, v in os.environ.items()}
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
    env["OLLAMA_MODELS"] = os.path.expanduser("~/.ollama/models")
    env["OLLAMA_MAX_LOADED_MODELS"] = "1"
    return subprocess.Popen(
        ["ollama", "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_ollama(host: str, timeout: int = 60) -> None:
    base = host if host.startswith("http") else f"http://{host}"
    url = f"{base}/api/tags"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    raise RuntimeError(f"Ollama server at {url} did not become ready within {timeout}s.")


def _ensure_model(ollama_host: str, model: str) -> None:
    base = ollama_host if ollama_host.startswith("http") else f"http://{ollama_host}"
    r = requests.get(f"{base}/api/tags", timeout=5)
    available = {m["name"] for m in r.json().get("models", [])}
    if model not in available:
        client = ollama.Client(host=ollama_host)
        for _ in client.pull(model, stream=True):
            pass


# ---------------------------------------------------------------------------
# Core LLM helper
# ---------------------------------------------------------------------------


def _get_formula_descriptors(
    passage_text: str,
    ollama_model: str,
    ollama_host: str,
    num_ctx: int,
) -> dict[str, list[str]]:
    client = ollama.Client(host=ollama_host)
    response = client.generate(
        model=ollama_model,
        system=SYSTEM_PROMPT,
        prompt=USER_TEMPLATE.format(passage=passage_text),
        options={"num_ctx": num_ctx},
        format=_Pairs.model_json_schema(),
    )
    pairs = _Pairs.model_validate_json(response.response)

    result: dict[str, list[str]] = {}
    for pair in pairs.pairs:
        match = _FORMULA_RE.search(pair.formula)
        if not match:
            continue
        result[match.group(1)] = pair.definitions

    return result


# ---------------------------------------------------------------------------
# Postgres helpers
# ---------------------------------------------------------------------------


def _fetch_passages(
    engine: Engine,
    silver_schema: str,
    overwrite: bool,
    limit: int | None,
) -> list[tuple[int, str]]:
    where = f"{TEXT_COLUMN} IS NOT NULL"
    if not overwrite:
        where += f" AND {OUTPUT_COLUMN} IS NULL"
    query = f"SELECT {ID_COLUMN}, {TEXT_COLUMN} FROM {silver_schema}.{POST_TABLE} WHERE {where}"
    if limit is not None:
        query += f" LIMIT {limit}"

    with engine.connect() as conn:
        rows = conn.execute(text(query)).fetchall()
    return [(row[0], row[1]) for row in rows]


def _flush(engine: Engine, silver_schema: str, buf: list[tuple[int, dict]]) -> None:
    if not buf:
        return
    update_sql = text(
        f"UPDATE {silver_schema}.{POST_TABLE} "
        f"SET {OUTPUT_COLUMN} = CAST(:val AS jsonb) "
        f"WHERE {ID_COLUMN} = :sid"
    )
    params = [{"val": json.dumps(descriptor_map), "sid": sid} for sid, descriptor_map in buf]
    with engine.begin() as conn:
        conn.execute(update_sql, params)
    buf.clear()


# ---------------------------------------------------------------------------
# Entry point used by main_extract_formula_descriptors.py
# ---------------------------------------------------------------------------


def build_formula_descriptors(
    engine: Engine,
    silver_schema: str,
    ollama_model: str = "llama3.2:3b",
    ollama_gpu: int = 0,
    ollama_port: int = 11434,
    num_ctx: int = 1024,
    write_buffer_size: int = 50,
    limit: int | None = None,
    overwrite: bool = False,
) -> int:
    ollama_host = f"http://127.0.0.1:{ollama_port}"

    passages = _fetch_passages(engine, silver_schema, overwrite, limit)
    print(f">>Found {len(passages)} passages to process for {silver_schema}.{POST_TABLE}.{OUTPUT_COLUMN}")
    if not passages:
        return 0

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        already_running = s.connect_ex(("127.0.0.1", ollama_port)) == 0

    ollama_proc = None if already_running else _start_ollama(ollama_gpu, ollama_port)
    if already_running:
        print(f">>Port {ollama_port} is already in use. Assuming it is Ollama and reusing it.")

    try:
        _wait_for_ollama(ollama_host)
        _ensure_model(ollama_host, ollama_model)

        write_buffer: list[tuple[int, dict]] = []
        total_written = 0
        with tqdm(total=len(passages), desc="extract_formula_descriptors", unit="passage") as pbar:
            for sid, passage_text in passages:
                if not _FORMULA_RE.search(passage_text):
                    # No formula placeholders: explicitly write {} instead of leaving it
                    # untouched, so a stale value from an earlier overwrite run doesn't linger.
                    write_buffer.append((sid, {}))
                else:
                    try:
                        descriptor_map = _get_formula_descriptors(
                            passage_text, ollama_model, ollama_host, num_ctx
                        )
                        write_buffer.append((sid, descriptor_map))
                    except Exception:
                        logger.warning("Descriptor extraction failed for silver_id=%s", sid, exc_info=True)
                        # Leave the existing value (if any) untouched so this row is retried next run.
                        pbar.update(1)
                        continue

                pbar.update(1)
                if len(write_buffer) >= write_buffer_size:
                    total_written += len(write_buffer)
                    _flush(engine, silver_schema, write_buffer)

        total_written += len(write_buffer)
        _flush(engine, silver_schema, write_buffer)
        return total_written
    finally:
        if ollama_proc is not None:
            ollama_proc.terminate()
