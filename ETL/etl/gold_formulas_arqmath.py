import logging
import re
from typing import Any

import networkx as nx
import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from tqdm import tqdm

from lib.math_lib.FormulaConversionHelper import FormulaConversionHelper

GOLD_TABLE = "formula"
logger = logging.getLogger(__name__)


def _nullable_str(value: Any) -> str | None:
    return str(value) if pd.notna(value) else None


def _sanitize_pmathml(pmathml: str) -> str:
    removed_alt_text = re.sub(r'alttext="([^;]*?)(")', "", pmathml)
    return removed_alt_text.replace("<<", "&lt; <").replace(">&<", "> &amp; <")


def _convert_row(row: pd.Series) -> dict:
    slt_nx_dict = None
    opt_nx_dict = None
    tangent_string_slt = None

    p_mathml: str | None = _nullable_str(row["p_mathml"])    
    c_mathml: str | None = _nullable_str(row["c_mathml"])
    visual_id = row["visual_id"]

    if p_mathml is not None:
        try:
            #this leads to 6231 instead of 10450 errors for 117514 formulas
            p_mathml = _sanitize_pmathml(p_mathml)
            
            slt_graph, tangent_string_slt = FormulaConversionHelper.get_slt_from_pmathml_string_and_tangent_string(p_mathml)
            slt_nx_dict = nx.node_link_data(slt_graph)
        except Exception:
            # logger.warning("SLT conversion failed for visual_id=%s", visual_id)
            pass
    if c_mathml is not None:
        try:
            opt_graph = FormulaConversionHelper.get_opt_from_cmathml_string(c_mathml)
            opt_nx_dict = nx.node_link_data(opt_graph)
        except Exception:
            # logger.warning("OPT conversion failed for visual_id=%s", visual_id)
            pass

    return {
        "visual_id": visual_id,
        "latex": _nullable_str(row["latex"]),
        "p_mathml": p_mathml,
        "c_mathml": c_mathml,
        "slt_nx_dict": slt_nx_dict,
        "opt_nx_dict": opt_nx_dict,
        "tangent_string_slt": tangent_string_slt,
    }


def build_gold_formulas(
    engine: Engine,
    silver_schema: str,
    gold_schema: str,
    chunk_size: int = 10_000,
) -> int:
    full_table = f"{gold_schema}.{GOLD_TABLE}"

    select_sql = text(
        f"""
        SELECT DISTINCT ON (visual_id) visual_id, latex, p_mathml, c_mathml
        FROM {silver_schema}.formula_arqmath
        WHERE visual_id IS NOT NULL
        ORDER BY visual_id, silver_id
        """
    )

    print(f">>Gold table {full_table}. From {silver_schema}.formula_arqmath")

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {full_table} RESTART IDENTITY"))

    total_rows = 0
    with engine.connect() as conn:
        for chunk in tqdm(
            pd.read_sql(select_sql, conn, chunksize=chunk_size),
            desc=GOLD_TABLE,
            unit="chunk",
        ):
            records = [
                r for _, row in chunk.iterrows()
                if (r := _convert_row(row))["slt_nx_dict"] is not None
                and r["opt_nx_dict"] is not None
            ]
            gold_df = pd.DataFrame(records)
            gold_df.to_sql(
                GOLD_TABLE,
                engine,
                schema=gold_schema,
                if_exists="append",
                index=False,
                dtype={"slt_nx_dict": JSONB(), "opt_nx_dict": JSONB()},  # type: ignore[arg-type]
            )
            total_rows += len(gold_df)

    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE {silver_schema}.formula_arqmath s
                SET fk_gold_formula = g.id
                FROM {gold_schema}.{GOLD_TABLE} g
                WHERE s.visual_id = g.visual_id
                """
            )
        )
        logger.info("Updated fk_gold_formula back-link on %s.formula_arqmath", silver_schema)

    return total_rows
