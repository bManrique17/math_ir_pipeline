"""Restrict a stage to the posts of one public.dataset row.

A dataset's posts are those linked to it through public.datasetxsilver_post
(dataset_id -> silver_post_id). Stages that accept a dataset_id use the helpers
here to validate it and to filter their post/formula queries; with
dataset_id=None they keep processing the full tables.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# public.datasetxsilver_post.silver_post_id has a FK to silver.post_arqmath, so a
# dataset's ids only mean something in these schemas, whatever
# silver_schema_prefix / gold_schema_prefix are (same reasoning as create_vocab.py).
DATASET_SILVER_SCHEMA = "silver"
DATASET_GOLD_SCHEMA = "gold"
DATASET_TABLE = "public.dataset"
DATASET_POST_TABLE = "public.datasetxsilver_post"


def dataset_post_filter(post_silver_id_expr: str) -> str:
    """SQL condition keeping only the dataset's posts; binds :dataset_id."""
    return (
        f"{post_silver_id_expr} IN "
        f"(SELECT silver_post_id FROM {DATASET_POST_TABLE} WHERE dataset_id = :dataset_id)"
    )


def resolve_dataset_schema(
    engine: Engine, dataset_id: int | None, schema: str, dataset_schema: str = DATASET_SILVER_SCHEMA
) -> str:
    """Return the schema a stage should use: `schema` as-is without a dataset, else the pinned one.

    Raises if dataset_id is set but missing from public.dataset.
    """
    if dataset_id is None:
        return schema

    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT d.name, (SELECT COUNT(*) FROM {DATASET_POST_TABLE} x WHERE x.dataset_id = d.id) AS n_posts "
                f"FROM {DATASET_TABLE} d WHERE d.id = :dataset_id"
            ),
            {"dataset_id": dataset_id},
        ).one_or_none()
    if row is None:
        raise ValueError(f"dataset_id={dataset_id} not found in {DATASET_TABLE}")

    print(f">>Restricting to dataset {dataset_id} ({row.name}): {row.n_posts} posts in schema {dataset_schema}")
    if schema != dataset_schema:
        logger.warning(
            "dataset_id=%s is set: using schema %s instead of the configured %s.",
            dataset_id, dataset_schema, schema,
        )
    return dataset_schema
