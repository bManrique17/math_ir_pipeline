from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tqdm import tqdm

BRONZE_COLUMNS = [
    "id",
    "post_id",
    "thread_id",
    "type",
    "comment_id",
    "old_visual_id",
    "visual_id",
    "issue",
    "formula",
]
INT_COLUMNS = ["id", "post_id", "thread_id", "comment_id", "old_visual_id", "visual_id"]


def load_bronze_source(engine: Engine, table: str, raw_dir: str) -> int:
    raw_path = Path(raw_dir)
    files = sorted(raw_path.glob("*.tsv"))

    full_table = f"bronze.{table}"
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {full_table}"))

    total_rows = 0
    print(f">>Table {table}. Directory {raw_dir}")
    for file_path in tqdm(files):
        df = pd.read_csv(file_path, sep="\t")[BRONZE_COLUMNS]
        df[INT_COLUMNS] = df[INT_COLUMNS].astype("Int64")
        df["source_file"] = file_path.name

        df.to_sql(table, engine, schema="bronze", if_exists="append", index=False)
        total_rows += len(df)

    return total_rows
