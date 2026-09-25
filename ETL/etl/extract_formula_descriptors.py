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

Rows are claimed in batches with `SELECT ... FOR UPDATE SKIP LOCKED`, stamping
formula_descriptors_claimed_at/_by, so this step is both resumable and safe to run
as several concurrent workers (same machine or different ones, each pointed at the
same Postgres) without two workers processing the same row. A claim that goes
stale (worker crashed mid-batch) is picked back up by anyone after
`stale_claim_minutes`. Within a single worker, up to `concurrency` LLM calls are
in flight at once via a thread pool, since Ollama itself can serve concurrent
generate() calls.

Rows whose LLM call failed are unclaimed immediately (and logged) so they get
retried without waiting for the staleness timeout.

Promoted from the standalone prototype at
DEBUG/extract_formula_descriptors/extract_descriptors_standalone.py.
"""

import json
import logging
import os
import re
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

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
CLAIM_COLUMN = "formula_descriptors_claimed_at"
CLAIM_BY_COLUMN = "formula_descriptors_claimed_by"

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
    client: ollama.Client,
    ollama_model: str,
    num_ctx: int,
) -> dict[str, list[str]]:
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


def _ensure_claim_columns(engine: Engine, silver_schema: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE {silver_schema}.{POST_TABLE} "
                f"ADD COLUMN IF NOT EXISTS {CLAIM_COLUMN} TIMESTAMPTZ"
            )
        )
        conn.execute(
            text(
                f"ALTER TABLE {silver_schema}.{POST_TABLE} "
                f"ADD COLUMN IF NOT EXISTS {CLAIM_BY_COLUMN} TEXT"
            )
        )
        # Partial index over still-pending rows so claiming stays cheap even
        # late in a run, when most of the table is already done.
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS idx_{POST_TABLE}_descriptors_pending "
                f"ON {silver_schema}.{POST_TABLE} (silver_id) "
                f"WHERE {OUTPUT_COLUMN} IS NULL AND {TEXT_COLUMN} IS NOT NULL"
            )
        )


def _count_pending(engine: Engine, silver_schema: str, overwrite: bool, limit: int | None) -> int:
    where = f"{TEXT_COLUMN} IS NOT NULL"
    if not overwrite:
        where += f" AND {OUTPUT_COLUMN} IS NULL"
    query = f"SELECT COUNT(*) FROM {silver_schema}.{POST_TABLE} WHERE {where}"
    with engine.connect() as conn:
        count = conn.execute(text(query)).scalar_one()
    return count if limit is None else min(count, limit)


def _claim_batch(
    engine: Engine,
    silver_schema: str,
    overwrite: bool,
    batch_size: int,
    stale_after: timedelta,
    worker_id: str,
) -> list[tuple[int, str]]:
    """Atomically claim up to batch_size unclaimed pending rows for this worker.

    Safe to call concurrently from multiple processes/machines: FOR UPDATE SKIP
    LOCKED means two callers never claim the same row, and the claim timestamp
    lets a stale claim (crashed worker) be picked up again after stale_after.
    """
    output_check = "TRUE" if overwrite else f"{OUTPUT_COLUMN} IS NULL"
    query = text(
        f"WITH claimed AS ("
        f"  SELECT {ID_COLUMN} FROM {silver_schema}.{POST_TABLE}"
        f"  WHERE {TEXT_COLUMN} IS NOT NULL"
        f"    AND ({output_check})"
        f"    AND ({CLAIM_COLUMN} IS NULL OR {CLAIM_COLUMN} < now() - :stale_after)"
        f"  ORDER BY {ID_COLUMN}"
        f"  LIMIT :batch_size"
        f"  FOR UPDATE SKIP LOCKED"
        f") "
        f"UPDATE {silver_schema}.{POST_TABLE} p "
        f"SET {CLAIM_COLUMN} = now(), {CLAIM_BY_COLUMN} = :worker_id "
        f"FROM claimed WHERE p.{ID_COLUMN} = claimed.{ID_COLUMN} "
        f"RETURNING p.{ID_COLUMN}, p.{TEXT_COLUMN}"
    )
    with engine.begin() as conn:
        rows = conn.execute(
            query, {"batch_size": batch_size, "stale_after": stale_after, "worker_id": worker_id}
        ).fetchall()
    return [(row[0], row[1]) for row in rows]


def _unclaim(engine: Engine, silver_schema: str, sid: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE {silver_schema}.{POST_TABLE} SET {CLAIM_COLUMN} = NULL WHERE {ID_COLUMN} = :sid"),
            {"sid": sid},
        )


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
    concurrency: int = 4,
    stale_claim_minutes: int = 30,
    worker_id: str | None = None,
) -> int:
    ollama_host = f"http://127.0.0.1:{ollama_port}"
    worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}"
    stale_after = timedelta(minutes=stale_claim_minutes)

    _ensure_claim_columns(engine, silver_schema)

    # Informational only: if other workers are running concurrently against the
    # same schema, this count (and the progress bar built from it) is a snapshot,
    # not this worker's exact share of the work.
    pending = _count_pending(engine, silver_schema, overwrite, limit)
    print(f">>Found {pending} passages to process for {silver_schema}.{POST_TABLE}.{OUTPUT_COLUMN}")
    if not pending:
        return 0

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        already_running = s.connect_ex(("127.0.0.1", ollama_port)) == 0

    ollama_proc = None if already_running else _start_ollama(ollama_gpu, ollama_port)
    if already_running:
        print(f">>Port {ollama_port} is already in use. Assuming it is Ollama and reusing it.")

    try:
        _wait_for_ollama(ollama_host)
        _ensure_model(ollama_host, ollama_model)
        client = ollama.Client(host=ollama_host)

        total_written = 0
        remaining = limit
        with tqdm(total=pending, desc="extract_formula_descriptors", unit="passage") as pbar:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                while remaining is None or remaining > 0:
                    batch_size = write_buffer_size if remaining is None else min(write_buffer_size, remaining)
                    batch = _claim_batch(
                        engine, silver_schema, overwrite, batch_size, stale_after, worker_id
                    )
                    if not batch:
                        break

                    write_buffer: list[tuple[int, dict]] = []
                    futures: dict = {}
                    for sid, passage_text in batch:
                        if not _FORMULA_RE.search(passage_text):
                            # No formula placeholders: explicitly write {} instead of leaving
                            # it untouched, so a stale value from an earlier overwrite run
                            # doesn't linger.
                            write_buffer.append((sid, {}))
                            pbar.update(1)
                        else:
                            future = pool.submit(
                                _get_formula_descriptors, passage_text, client, ollama_model, num_ctx
                            )
                            futures[future] = sid

                    for future in as_completed(futures):
                        sid = futures[future]
                        try:
                            descriptor_map = future.result()
                            write_buffer.append((sid, descriptor_map))
                        except Exception:
                            logger.warning("Descriptor extraction failed for silver_id=%s", sid, exc_info=True)
                            # Unclaim so this row is retried on the next batch/run instead of
                            # waiting for the staleness timeout.
                            _unclaim(engine, silver_schema, sid)
                        pbar.update(1)

                    total_written += len(write_buffer)
                    _flush(engine, silver_schema, write_buffer)
                    if remaining is not None:
                        remaining -= len(batch)

        return total_written
    finally:
        if ollama_proc is not None:
            ollama_proc.terminate()
