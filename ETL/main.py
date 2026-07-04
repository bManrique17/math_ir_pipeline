import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, text

from ETL.etl.bronze_formulas_arqmath import load_bronze_source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent / "sql"


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:

    engine = create_engine(cfg.db.postgres_connection_string)

    with engine.begin() as conn:
        conn.execute(text((SQL_DIR / "bronze_schema.sql").read_text()))

    for source in cfg.bronze_sources:
        load_bronze_source(engine, source.table, source.dir)


if __name__ == "__main__":
    main()
