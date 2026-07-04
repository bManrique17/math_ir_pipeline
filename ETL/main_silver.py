import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig
from sqlalchemy import create_engine, text

from ETL.etl.silver_formulas_arqmath import build_silver_formulas
from ETL.etl.silver_posts_arqmath import build_silver_posts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent / "sql"


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:

    engine = create_engine(cfg.db.postgres_connection_string)
    silver_schema = cfg.silver_schema_prefix

    with engine.begin() as conn:
        conn.execute(text((SQL_DIR / "silver_schema.sql").read_text().format(schema=silver_schema)))

    if cfg.silver_load_formulas:
        build_silver_formulas(
            engine,
            bronze_schema=cfg.bronze_schema_prefix,
            silver_schema=silver_schema,
            latex_table=cfg.silver_formula.latex_table,
            p_mathml_table=cfg.silver_formula.p_mathml_table,
            c_mathml_table=cfg.silver_formula.c_mathml_table,
        )

    if cfg.silver_load_posts:
        build_silver_posts(
            engine,
            bronze_schema=cfg.bronze_schema_prefix,
            silver_schema=silver_schema,
            post_table=cfg.silver_post.post_table,
        )


if __name__ == "__main__":
    main()
