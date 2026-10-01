import logging

import hydra
from omegaconf import DictConfig
from sqlalchemy import create_engine

from etl.create_vocab import build_vocab

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    engine = create_engine(cfg.db.postgres_connection_string)

    vocab_id = build_vocab(
        engine,
        dataset_id=cfg.vocab.dataset_id,
        comments=cfg.vocab.comments,
        overwrite=cfg.vocab.overwrite,
    )
    print(f">>Vocab id: {vocab_id}")


if __name__ == "__main__":
    main()
