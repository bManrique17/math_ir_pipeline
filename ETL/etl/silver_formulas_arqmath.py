from sqlalchemy import text
from sqlalchemy.engine import Engine

SILVER_TABLE = "formula_arqmath"


def build_silver_formulas(
    engine: Engine,
    bronze_schema: str,
    silver_schema: str,
    latex_table: str,
    p_mathml_table: str,
    c_mathml_table: str,
) -> int:
    full_table = f"{silver_schema}.{SILVER_TABLE}"

    insert_sql = text(
        f"""
        INSERT INTO {full_table} (id, visual_id, latex, p_mathml, c_mathml)
        SELECT l.id, l.visual_id, l.formula AS latex, s.formula AS p_mathml, o.formula AS c_mathml
        FROM {bronze_schema}.{latex_table} l
        JOIN {bronze_schema}.{p_mathml_table} s ON s.id = l.id
        JOIN {bronze_schema}.{c_mathml_table} o ON o.id = l.id
        """
    )

    print(f">>Silver table {full_table}. From {bronze_schema}.{{{latex_table},{p_mathml_table},{c_mathml_table}}}")
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {full_table}"))
        result = conn.execute(insert_sql)
        return result.rowcount
