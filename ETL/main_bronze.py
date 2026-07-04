import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, text

from ETL.etl.bronze_formulas_arqmath import load_bronze_source as load_bronze_formulas
from ETL.etl.bronze_post_arqmath import load_bronze_source as load_bronze_posts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent / "sql"


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:

    engine = create_engine(cfg.db.postgres_connection_string)
    schema = cfg.bronze_schema_prefix

    with engine.begin() as conn:
        conn.execute(text((SQL_DIR / "bronze_schema.sql").read_text().format(schema=schema)))

    if cfg.bronze_load_formulas:
        for source in cfg.formula_sources:
            load_bronze_formulas(engine, source.table, source.dir, schema=schema)

    if cfg.bronze_load_posts:
        for source in cfg.post_sources:
            load_bronze_posts(engine, source.table, source.path, schema=schema, chunk_size=cfg.chunk_size)


if __name__ == "__main__":
    main()
