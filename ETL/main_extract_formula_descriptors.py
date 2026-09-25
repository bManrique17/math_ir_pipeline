import logging

import hydra
from omegaconf import DictConfig
from sqlalchemy import create_engine

from etl.extract_formula_descriptors import build_formula_descriptors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    if not cfg.descriptors_load_formula_descriptors:
        logger.info("descriptors_load_formula_descriptors is false, skipping.")
        return

    engine = create_engine(cfg.db.postgres_connection_string)

    n = build_formula_descriptors(
        engine,
        silver_schema=cfg.silver_schema_prefix,
        ollama_model=cfg.descriptors.ollama_model,
        ollama_gpu=cfg.descriptors.ollama_gpu,
        ollama_port=cfg.descriptors.ollama_port,
        num_ctx=cfg.descriptors.num_ctx,
        write_buffer_size=cfg.descriptors.write_buffer_size,
        limit=cfg.descriptors.limit,
        overwrite=cfg.descriptors.overwrite,
    )
    print(f">>Formula descriptors written: {n}")


if __name__ == "__main__":
    main()
