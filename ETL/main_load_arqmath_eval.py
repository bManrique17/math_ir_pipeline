import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig
from sqlalchemy import create_engine, text

from etl.load_arqmath_eval import load_task1, load_task2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent / "sql"


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    engine = create_engine(cfg.db.postgres_connection_string)
    eval_dir = Path(cfg.paths.arqmath_eval_dir)

    with engine.begin() as conn:
        conn.execute(text((SQL_DIR / "public_eval_schema.sql").read_text()))

    if cfg.eval_load_task1:
        load_task1(engine, eval_dir)
    if cfg.eval_load_task2:
        load_task2(engine, eval_dir)


if __name__ == "__main__":
    main()
