import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tqdm import tqdm

from etl.silver_posts_arqmath import (
    _replace_math_spans,
    _strip_tags_and_normalize_whitespace,
    _title_and_body,
)


def _load_formula_id_to_fk_gold(engine: Engine, silver_schema: str) -> dict[int, int]:
    query = text(f"SELECT id, fk_gold_formula FROM {silver_schema}.formula_arqmath")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    df["id"] = df["id"].astype(int)
    df["fk_gold_formula"] = df["fk_gold_formula"].fillna(-1).astype(int)
    return dict(zip(df["id"], df["fk_gold_formula"]))


def _compute_text(row: pd.Series, id_to_fk_gold: dict[int, int]) -> str | None:
    combined = _title_and_body(row)
    if not combined:
        return None

    def _resolve(formula_id: str) -> str:
        return str(id_to_fk_gold.get(int(formula_id), -1))

    with_placeholders = _replace_math_spans(combined, _resolve)
    if with_placeholders is None:
        return None
    return _strip_tags_and_normalize_whitespace(with_placeholders) or None


def update_silver_posts_fk_gold(
    engine: Engine,
    silver_schema: str,
    chunk_size: int = 50_000,
) -> int:
    select_sql = text(f"SELECT silver_id, title, body FROM {silver_schema}.post_arqmath")
    update_sql = text(
        f"UPDATE {silver_schema}.post_arqmath "
        f"SET normalized_text_placeholders_fk_gold_formula = :val "
        f"WHERE silver_id = :sid"
    )

    id_to_fk_gold = _load_formula_id_to_fk_gold(engine, silver_schema)
    print(f">>Loaded {len(id_to_fk_gold)} formula→gold mappings")

    total_rows = 0
    with engine.connect() as read_conn:
        for chunk in tqdm(
            pd.read_sql(select_sql, read_conn, chunksize=chunk_size),
            desc="update_silver_posts_fk_gold",
            unit="chunk",
        ):
            params = [
                {"val": _compute_text(row, id_to_fk_gold), "sid": row["silver_id"]}
                for _, row in chunk.iterrows()
            ]
            with engine.begin() as write_conn:
                write_conn.execute(update_sql, params)
            total_rows += len(chunk)

    return total_rows
