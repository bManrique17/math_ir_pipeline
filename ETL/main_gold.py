import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig
from sqlalchemy import create_engine, text

from etl.gold_formulas_arqmath import build_gold_formulas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent / "sql"


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:

    engine = create_engine(cfg.db.postgres_connection_string)
    gold_schema = cfg.gold_schema_prefix

    with engine.begin() as conn:
        conn.execute(text((SQL_DIR / "gold_schema.sql").read_text().format(schema=gold_schema)))

    if cfg.gold_load_formulas:
        n = build_gold_formulas(
            engine,
            silver_schema=cfg.silver_schema_prefix,
            gold_schema=gold_schema,
            chunk_size=cfg.chunk_size,
        )
        logger.info("Gold formulas inserted: %d", n)


if __name__ == "__main__":
    main()
