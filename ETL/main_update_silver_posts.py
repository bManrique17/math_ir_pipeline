import hydra
from omegaconf import DictConfig
from sqlalchemy import create_engine

from etl.update_silver_posts_fk_gold import update_silver_posts_fk_gold


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    engine = create_engine(cfg.db.postgres_connection_string)

    n = update_silver_posts_fk_gold(
        engine,
        silver_schema=cfg.silver_schema_prefix,
        chunk_size=cfg.chunk_size,
    )
    print(f">>Silver posts updated with fk_gold_formula placeholders: {n}")


if __name__ == "__main__":
    main()
