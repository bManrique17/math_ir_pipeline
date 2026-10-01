"""Build SLT/OPT node and edge vocabularies for a dataset and store them in public.vocab.

The formulas of a dataset are those linked to it through
public.datasetxgold_formula (dataset_id -> gold_formula_id), joined with
gold.formula on id. Each formula's slt_nx_dict / opt_nx_dict is an
nx.node_link_data graph; a node's token is its "original_tag" (e.g. "V!x",
"U!+") and an edge's token is its "label" (e.g. "n", "a" in SLT; the argument
position, e.g. "0", "1", in OPT), falling back to "<UNK>" when missing.

Token counts are computed in Postgres (jsonb_array_elements + GROUP BY), so
nothing but the final per-token counts ever leaves the database. Vocab ids
follow the previous LMDB-based builder (DEBUG/create_vocabs_old.py): "<PAD>" is
0 and the remaining tokens are numbered from 1 by descending frequency (ties
broken by token, so the result is deterministic).

One row is written to public.vocab per run:
- slt / opt:                   node id (str) -> token, e.g. {"2": "V!x"}
- slt_inverted / opt_inverted: token -> node id (int), e.g. {"V!x": 2}
- slt_count / opt_count:       token -> occurrences, e.g. {"V!x": 120}
- slt_edge / opt_edge:         edge id (str) -> edge label, e.g. {"1": "n"}
- slt_edge_inverted / opt_edge_inverted: edge label -> edge id (int), e.g. {"n": 1}
- slt_edge_count / opt_edge_count: edge label -> occurrences, e.g. {"n": 87}

public.vocab has no uniqueness on dataset_id, so a dataset that already has a
vocab is skipped unless overwrite=True, which replaces it in the same
transaction.

Collection stats from the old builder are not produced: public.vocab has no
columns for them.
"""

import json
import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger(__name__)

# public.datasetxgold_formula.gold_formula_id has a FK to gold.formula, so the
# gold schema is fixed here rather than taken from gold_schema_prefix.
GOLD_SCHEMA = "gold"
DATASET_TABLE = "public.dataset"
DATASET_FORMULA_TABLE = "public.datasetxgold_formula"
VOCAB_TABLE = "public.vocab"

PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"


def _count_tokens(
    conn: Connection, dataset_id: int, graph_column: str, elements_key: str, token_key: str
) -> dict[str, int]:
    """Count token_key values over the elements_key ("nodes"/"edges") array of every graph."""
    query = text(
        f"""
        SELECT COALESCE(el->>'{token_key}', :unk) AS token, COUNT(*) AS cnt
        FROM {DATASET_FORMULA_TABLE} d
        JOIN {GOLD_SCHEMA}.formula f ON f.id = d.gold_formula_id
        CROSS JOIN LATERAL jsonb_array_elements(f.{graph_column}->'{elements_key}') AS el
        WHERE d.dataset_id = :dataset_id
        GROUP BY 1
        """
    )
    rows = conn.execute(query, {"dataset_id": dataset_id, "unk": UNK_TOKEN}).fetchall()
    return {row.token: row.cnt for row in rows}


def _build_vocab(freq: dict[str, int]) -> tuple[dict[str, str], dict[str, int], dict[str, int]]:
    sorted_tokens = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    vocab: dict[str, str] = {"0": PAD_TOKEN}
    inverted: dict[str, int] = {PAD_TOKEN: 0}
    count: dict[str, int] = {PAD_TOKEN: 0}
    for idx, (token, cnt) in enumerate(sorted_tokens, start=1):
        vocab[str(idx)] = token
        inverted[token] = idx
        count[token] = cnt
    return vocab, inverted, count


# ---------------------------------------------------------------------------
# Entry point used by main_create_vocab.py
# ---------------------------------------------------------------------------


def build_vocab(
    engine: Engine,
    dataset_id: int,
    comments: str | None = None,
    overwrite: bool = False,
) -> int:
    """Create the public.vocab row for dataset_id and return its id."""
    with engine.begin() as conn:
        dataset_name = conn.execute(
            text(f"SELECT name FROM {DATASET_TABLE} WHERE id = :dataset_id"),
            {"dataset_id": dataset_id},
        ).scalar_one_or_none()
        if dataset_name is None:
            raise ValueError(f"dataset_id={dataset_id} not found in {DATASET_TABLE}")

        existing_ids = conn.execute(
            text(f"SELECT id FROM {VOCAB_TABLE} WHERE dataset_id = :dataset_id ORDER BY id"),
            {"dataset_id": dataset_id},
        ).scalars().all()
        if existing_ids and not overwrite:
            logger.info(
                "Vocab already exists for dataset_id=%s (vocab ids %s); pass overwrite=true to rebuild.",
                dataset_id, existing_ids,
            )
            return existing_ids[-1]

        num_formulas = conn.execute(
            text(f"SELECT COUNT(*) FROM {DATASET_FORMULA_TABLE} WHERE dataset_id = :dataset_id"),
            {"dataset_id": dataset_id},
        ).scalar_one()
        print(f">>Building vocabs for dataset {dataset_id} ({dataset_name}) from {num_formulas} formulas")

        slt, slt_inverted, slt_count = _build_vocab(
            _count_tokens(conn, dataset_id, "slt_nx_dict", "nodes", "original_tag")
        )
        opt, opt_inverted, opt_count = _build_vocab(
            _count_tokens(conn, dataset_id, "opt_nx_dict", "nodes", "original_tag")
        )
        slt_edge, slt_edge_inverted, slt_edge_count = _build_vocab(
            _count_tokens(conn, dataset_id, "slt_nx_dict", "edges", "label")
        )
        opt_edge, opt_edge_inverted, opt_edge_count = _build_vocab(
            _count_tokens(conn, dataset_id, "opt_nx_dict", "edges", "label")
        )

        if existing_ids:
            conn.execute(
                text(f"DELETE FROM {VOCAB_TABLE} WHERE dataset_id = :dataset_id"),
                {"dataset_id": dataset_id},
            )
            logger.info("Deleted previous vocab ids %s for dataset_id=%s", existing_ids, dataset_id)

        vocab_id = conn.execute(
            text(
                f"""
                INSERT INTO {VOCAB_TABLE}
                    (dataset_id, comments, slt, opt, slt_inverted, opt_inverted, slt_count, opt_count,
                     slt_edge, opt_edge, slt_edge_inverted, opt_edge_inverted, slt_edge_count, opt_edge_count)
                VALUES
                    (:dataset_id, :comments,
                     CAST(:slt AS jsonb), CAST(:opt AS jsonb),
                     CAST(:slt_inverted AS jsonb), CAST(:opt_inverted AS jsonb),
                     CAST(:slt_count AS jsonb), CAST(:opt_count AS jsonb),
                     CAST(:slt_edge AS jsonb), CAST(:opt_edge AS jsonb),
                     CAST(:slt_edge_inverted AS jsonb), CAST(:opt_edge_inverted AS jsonb),
                     CAST(:slt_edge_count AS jsonb), CAST(:opt_edge_count AS jsonb))
                RETURNING id
                """
            ),
            {
                "dataset_id": dataset_id,
                "comments": comments or f"node/edge vocabs from {num_formulas} gold formulas of dataset '{dataset_name}'",
                "slt": json.dumps(slt),
                "opt": json.dumps(opt),
                "slt_inverted": json.dumps(slt_inverted),
                "opt_inverted": json.dumps(opt_inverted),
                "slt_count": json.dumps(slt_count),
                "opt_count": json.dumps(opt_count),
                "slt_edge": json.dumps(slt_edge),
                "opt_edge": json.dumps(opt_edge),
                "slt_edge_inverted": json.dumps(slt_edge_inverted),
                "opt_edge_inverted": json.dumps(opt_edge_inverted),
                "slt_edge_count": json.dumps(slt_edge_count),
                "opt_edge_count": json.dumps(opt_edge_count),
            },
        ).scalar_one()

    logger.info(
        "Vocab id=%s for dataset_id=%s: slt=%d, opt=%d, slt_edge=%d, opt_edge=%d tokens (incl. %s)",
        vocab_id, dataset_id, len(slt), len(opt), len(slt_edge), len(opt_edge), PAD_TOKEN,
    )
    return vocab_id
