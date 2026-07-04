from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tqdm import tqdm

ATTRIBUTE_TO_COLUMN = {
    "Id": "id",
    "PostTypeId": "post_type_id",
    "AcceptedAnswerId": "accepted_answer_id",
    "ParentId": "parent_id",
    "CreationDate": "creation_date",
    "DeletionDate": "deletion_date",
    "Score": "score",
    "ViewCount": "view_count",
    "Body": "body",
    "OwnerUserId": "owner_user_id",
    "OwnerDisplayName": "owner_display_name",
    "LastEditorUserId": "last_editor_user_id",
    "LastEditorDisplayName": "last_editor_display_name",
    "LastEditDate": "last_edit_date",
    "LastActivityDate": "last_activity_date",
    "Title": "title",
    "Tags": "tags",
    "AnswerCount": "answer_count",
    "CommentCount": "comment_count",
    "FavoriteCount": "favorite_count",
    "ClosedDate": "closed_date",
    "CommunityOwnedDate": "community_owned_date",
    "ContentLicense": "content_license",
}
BRONZE_COLUMNS = list(ATTRIBUTE_TO_COLUMN.values())
INT_COLUMNS = [
    "id",
    "post_type_id",
    "accepted_answer_id",
    "parent_id",
    "score",
    "view_count",
    "owner_user_id",
    "last_editor_user_id",
    "answer_count",
    "comment_count",
    "favorite_count",
]
DATE_COLUMNS = [
    "creation_date",
    "deletion_date",
    "last_edit_date",
    "last_activity_date",
    "closed_date",
    "community_owned_date",
]
CHUNK_SIZE = 50_000


def _iter_row_dicts(file_path: Path):
    for _, elem in ET.iterparse(file_path, events=("end",)):
        if elem.tag != "row":
            continue
        yield {column: elem.attrib.get(attribute) for attribute, column in ATTRIBUTE_TO_COLUMN.items()}
        elem.clear()


def _to_dataframe(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=BRONZE_COLUMNS)
    df[INT_COLUMNS] = df[INT_COLUMNS].apply(pd.to_numeric, errors="coerce").astype("Int64")
    df[DATE_COLUMNS] = df[DATE_COLUMNS].apply(pd.to_datetime)
    return df


def _flush_chunk(rows: list, engine: Engine, table: str, schema: str, source_file: str) -> int:
    df = _to_dataframe(rows)
    df["source_file"] = source_file
    df.to_sql(table, engine, schema=schema, if_exists="append", index=False)
    return len(df)


def load_bronze_source(
    engine: Engine, table: str, xml_path: str, schema: str = "bronze", chunk_size: int = CHUNK_SIZE
) -> int:
    file_path = Path(xml_path)

    full_table = f"{schema}.{table}"
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {full_table}"))

    print(f">>Table {table}. File {xml_path}")
    total_rows = 0
    chunk = []
    for row in tqdm(_iter_row_dicts(file_path), desc=file_path.name, unit="row"):
        chunk.append(row)
        if len(chunk) >= chunk_size:
            total_rows += _flush_chunk(chunk, engine, table, schema, file_path.name)
            chunk = []

    if chunk:
        total_rows += _flush_chunk(chunk, engine, table, schema, file_path.name)

    return total_rows
