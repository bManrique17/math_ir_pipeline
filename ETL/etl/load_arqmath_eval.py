"""Load the ARQMath evaluation topics and qrels into the public schema.

Expected layout under eval_dir:
    Task1/ARQMath{1,2,3}/topics.xml, qrels.tsv
    Task2/ARQMath{1,2,3}/topics.xml, qrels_formula_id.tsv, qrels_visual_id.tsv

Qrels are 4 tab-separated columns without header: topic id, unused, doc id
(post id / formula id / visual id), relevance.

Topics keep the topic number plus Title and Question (Task 2 also Formula_Id and
Latex); Tags are ignored. raw_content is "Title Question" as HTML;
normalized_content strips the HTML and writes every math-container span as
$latex$ (single dollars, whatever delimiters the span had, since some spans have
none or are malformed, e.g. "$1").

qrels_task2_formula_id.post_id is looked up in silver.formula_arqmath (id ->
post_id) inside Postgres. Each table is replaced per ARQMath version in one
transaction, so reruns are idempotent.
"""

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from etl.silver_posts_arqmath import _strip_tags_and_normalize_whitespace

logger = logging.getLogger(__name__)

# silver.formula_arqmath is fixed (not silver_schema_prefix): it's the full
# ARQMath formula collection the qrels refer to.
SILVER_FORMULA_TABLE = "silver.formula_arqmath"

TOPICS_TASK1_TABLE = "public.topics_task1"
TOPICS_TASK2_TABLE = "public.topics_task2"
QRELS_TASK1_TABLE = "public.qrels_task1"
QRELS_TASK2_VISUAL_TABLE = "public.qrels_task2_visual_id"
QRELS_TASK2_FORMULA_TABLE = "public.qrels_task2_formula_id"

_VERSION_DIR_RE = re.compile(r"^ARQMath(?P<version>\d+)$")
# <span class="math-container" id="q_4">$$f(x)= ...$$</span>
_MATH_SPAN_RE = re.compile(
    r'<span(?=[^>]*\bclass="math-container")[^>]*>(?P<latex>.*?)</span>',
    re.DOTALL,
)


def _version_dirs(task_dir: Path) -> list[tuple[int, Path]]:
    dirs = []
    for d in sorted(task_dir.iterdir()):
        m = _VERSION_DIR_RE.match(d.name)
        if d.is_dir() and m:
            dirs.append((int(m.group("version")), d))
    if not dirs:
        raise FileNotFoundError(f"No ARQMath<n> folders in {task_dir}")
    return dirs


def _math_span_to_dollars(m: re.Match) -> str:
    latex = m.group("latex").strip().strip("$").strip()
    return f" ${latex}$ "


def normalize_topic_content(raw: str) -> str | None:
    with_dollars = _MATH_SPAN_RE.sub(_math_span_to_dollars, raw)
    return _strip_tags_and_normalize_whitespace(with_dollars) or None


def _topic_text(topic: ET.Element, tag: str) -> str:
    return (topic.findtext(tag) or "").strip()


def parse_topics(path: Path, version: int, with_formula: bool) -> pd.DataFrame:
    rows = []
    for topic in ET.parse(path).getroot().findall("Topic"):
        raw = f"{_topic_text(topic, 'Title')} {_topic_text(topic, 'Question')}".strip()
        row = {
            "topic_id": topic.get("number"),
            "raw_content": raw or None,
            "normalized_content": normalize_topic_content(raw),
            "arqmath_version": version,
        }
        if with_formula:
            row["formula_id"] = _topic_text(topic, "Formula_Id") or None
            row["formula_latex"] = _topic_text(topic, "Latex") or None
        rows.append(row)
    return pd.DataFrame(rows)


def parse_qrels(path: Path, version: int, id_column: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", header=None, dtype=str, usecols=[0, 2, 3])
    df = df.apply(lambda col: col.str.strip())  # some files have CRLF endings
    df.columns = ["topic_id", id_column, "relevance"]
    df[id_column] = df[id_column].astype("int64")
    df["relevance"] = df["relevance"].astype("int16")
    df["arqmath_version"] = version
    return df


def _replace_version(conn: Connection, table: str, df: pd.DataFrame, version: int) -> None:
    schema, name = table.split(".")
    conn.execute(text(f"DELETE FROM {table} WHERE arqmath_version = :v"), {"v": version})
    df.to_sql(name, conn, schema=schema, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f">>{table} ARQMath{version}: {len(df)} rows")


def _fill_formula_post_ids(conn: Connection, version: int) -> None:
    conn.execute(
        text(
            f"""
            UPDATE {QRELS_TASK2_FORMULA_TABLE} q
            SET post_id = f.post_id
            FROM {SILVER_FORMULA_TABLE} f
            WHERE f.id = q.formula_id AND q.arqmath_version = :v
            """
        ),
        {"v": version},
    )
    missing = conn.execute(
        text(
            f"SELECT COUNT(*) FROM {QRELS_TASK2_FORMULA_TABLE} "
            f"WHERE arqmath_version = :v AND post_id IS NULL"
        ),
        {"v": version},
    ).scalar_one()
    if missing:
        logger.warning(
            "%s ARQMath%d: %d formula ids not found in %s (post_id NULL)",
            QRELS_TASK2_FORMULA_TABLE, version, missing, SILVER_FORMULA_TABLE,
        )


def load_task1(engine: Engine, eval_dir: Path) -> None:
    for version, d in _version_dirs(eval_dir / "Task1"):
        topics = parse_topics(d / "topics.xml", version, with_formula=False)
        qrels = parse_qrels(d / "qrels.tsv", version, "post_id")
        with engine.begin() as conn:
            _replace_version(conn, TOPICS_TASK1_TABLE, topics, version)
            _replace_version(conn, QRELS_TASK1_TABLE, qrels, version)


def load_task2(engine: Engine, eval_dir: Path) -> None:
    for version, d in _version_dirs(eval_dir / "Task2"):
        topics = parse_topics(d / "topics.xml", version, with_formula=True)
        visual = parse_qrels(d / "qrels_visual_id.tsv", version, "visual_id")
        formula = parse_qrels(d / "qrels_formula_id.tsv", version, "formula_id")
        with engine.begin() as conn:
            _replace_version(conn, TOPICS_TASK2_TABLE, topics, version)
            _replace_version(conn, QRELS_TASK2_VISUAL_TABLE, visual, version)
            _replace_version(conn, QRELS_TASK2_FORMULA_TABLE, formula, version)
            _fill_formula_post_ids(conn, version)
