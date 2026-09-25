import os

from sqlalchemy import create_engine

PG_DSN = os.environ.get("PG_DSN", "postgresql://postgres:postgres@localhost:5432/math_ir")
PG_SCHEMA = os.environ.get("PG_SCHEMA", "debug_silver")
PG_GOLD_SCHEMA = os.environ.get("PG_GOLD_SCHEMA", "debug_gold")

engine = create_engine(PG_DSN)
