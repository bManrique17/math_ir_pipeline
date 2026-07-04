import hydra
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, text


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    print(OmegaConf.to_yaml(cfg))

    engine = create_engine(cfg.db.postgres_connection_string)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


if __name__ == "__main__":
    main()
