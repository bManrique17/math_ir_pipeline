import logging

import hydra
from omegaconf import DictConfig
from sqlalchemy import create_engine

from etl.annotate_opt_formulas import build_opt_annotations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    if not cfg.silver_load_opt_annotations:
        logger.info("silver_load_opt_annotations is false, skipping.")
        return

    engine = create_engine(cfg.db.postgres_connection_string)

    n = build_opt_annotations(
        engine,
        silver_schema=cfg.silver_schema_prefix,
        gold_schema=cfg.gold_schema_prefix,
        chunk_size=cfg.chunk_size,
    )
    print(f">>Annotated OPT graphs written: {n}")


if __name__ == "__main__":
    main()
