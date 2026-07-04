import html
import re

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tqdm import tqdm

SILVER_TABLE = "post_arqmath"
CHUNK_SIZE = 50_000

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_LINEBREAK_RE = re.compile(r"[\r\n\t\f\v]+")
_MULTI_SPACE_RE = re.compile(r" {2,}")
# <span class="math-container" id="336">\text {{1,1,2,3,5,8,13,....}}</span>
_MATH_SPAN_RE = re.compile(
    r'<span(?=[^>]*\bclass="math-container")(?=[^>]*\bid="(?P<id>\d+)")[^>]*>.*?</span>',
    re.DOTALL,
)


def _field(row: pd.Series, name: str) -> str:
    value = row[name]
    return "" if pd.isna(value) else str(value)


def _title_and_body(row: pd.Series) -> str:
    return f"{_field(row, 'title')} {_field(row, 'body')}".strip()


def _strip_tags_and_normalize_whitespace(text: str) -> str:
    without_tags = _HTML_TAG_RE.sub(" ", text)
    unescaped = html.unescape(without_tags)
    without_linebreaks = _LINEBREAK_RE.sub(" ", unescaped)
    return _MULTI_SPACE_RE.sub(" ", without_linebreaks).strip()


def compute_normalized_text_and_latex(row: pd.Series) -> str | None:
    combined = _title_and_body(row)
    if not combined:
        return None

    return _strip_tags_and_normalize_whitespace(combined) or None


def _replace_math_spans(text: str, resolve) -> str | None:
    return _MATH_SPAN_RE.sub(lambda m: f"[{resolve(m.group('id'))}]", text)


def compute_normalized_text_placeholders_formula_id(row: pd.Series) -> str | None:
    combined = _title_and_body(row)
    if not combined:
        return None

    with_placeholders = _replace_math_spans(combined, lambda formula_id: formula_id)
    return _strip_tags_and_normalize_whitespace(with_placeholders) or None


def compute_normalized_text_placeholders_visual_id(row: pd.Series, id_to_visual_id: dict) -> str | None:
    combined = _title_and_body(row)
    if not combined:
        return None

    def _resolve(formula_id: str) -> str:
        visual_id = id_to_visual_id.get(int(formula_id))
        return "-1" if visual_id is None or pd.isna(visual_id) else str(int(visual_id))

    with_placeholders = _replace_math_spans(combined, _resolve)
    return _strip_tags_and_normalize_whitespace(with_placeholders) or None


def compute_formula_descriptors(row: pd.Series) -> dict | None:
    return None


def compute_normalized_text_placeholders_fk_gold_formula(row: pd.Series) -> str | None:
    return None


def _load_formula_id_to_visual_id(engine: Engine, silver_schema: str) -> dict:
    query = text(f"SELECT id, visual_id FROM {silver_schema}.formula_arqmath")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return dict(zip(df["id"], df["visual_id"]))


def _enrich_chunk(df: pd.DataFrame, id_to_visual_id: dict) -> pd.DataFrame:
    df["normalized_text_and_latex"] = df.apply(compute_normalized_text_and_latex, axis=1)
    df["normalized_text_placeholders_formula_id"] = df.apply(
        compute_normalized_text_placeholders_formula_id, axis=1
    )
    df["normalized_text_placeholders_visual_id"] = df.apply(
        lambda row: compute_normalized_text_placeholders_visual_id(row, id_to_visual_id), axis=1
    )
    df["formula_descriptors"] = df.apply(compute_formula_descriptors, axis=1)
    df["normalized_text_placeholders_fk_gold_formula"] = df.apply(
        compute_normalized_text_placeholders_fk_gold_formula, axis=1
    )
    return df


def build_silver_posts(
    engine: Engine,
    bronze_schema: str,
    silver_schema: str,
    post_table: str,
    chunk_size: int = CHUNK_SIZE,
) -> int:
    full_table = f"{silver_schema}.{SILVER_TABLE}"

    select_sql = text(f"SELECT id, title, body, post_type_id FROM {bronze_schema}.{post_table}")

    print(f">>Silver table {full_table}. From {bronze_schema}.{post_table}")
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {full_table}"))

    id_to_visual_id = _load_formula_id_to_visual_id(engine, silver_schema)

    total_rows = 0
    with engine.connect() as conn:
        for chunk in tqdm(pd.read_sql(select_sql, conn, chunksize=chunk_size), desc=post_table, unit="chunk"):
            chunk = _enrich_chunk(chunk, id_to_visual_id)
            chunk.to_sql(SILVER_TABLE, engine, schema=silver_schema, if_exists="append", index=False)
            total_rows += len(chunk)

    return total_rows
