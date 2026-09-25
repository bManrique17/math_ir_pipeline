from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..db import PG_GOLD_SCHEMA, PG_SCHEMA, engine
from ..render import build_formula_graph_view
from ..schemas import FormulaGraphOut, FormulaListItemOut, FormulaListOut

router = APIRouter()

_SELECT_FORMULA_GRAPH = (
    "SELECT f.id, f.latex, f.opt_nx_dict_annotated, g.opt_nx_dict, g.slt_nx_dict "
    f"FROM {PG_SCHEMA}.formula_arqmath f "
    f"LEFT JOIN {PG_GOLD_SCHEMA}.formula g ON g.id = f.fk_gold_formula "
    "WHERE f.id = :id"
)

_MAX_LIMIT = 100


@router.get("/formulas", response_model=FormulaListOut)
def list_formulas(offset: int = 0, limit: int = 20) -> FormulaListOut:
    limit = max(1, min(limit, _MAX_LIMIT))
    query = text(
        f"SELECT id, latex FROM {PG_SCHEMA}.formula_arqmath ORDER BY id LIMIT :limit OFFSET :offset"
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit + 1, "offset": offset}).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [FormulaListItemOut(id=row.id, latex=row.latex) for row in rows]
    return FormulaListOut(items=items, has_more=has_more)


@router.get("/formulas/{id}", response_model=FormulaListItemOut)
def get_formula(id: int) -> FormulaListItemOut:
    query = text(f"SELECT id, latex FROM {PG_SCHEMA}.formula_arqmath WHERE id = :id")
    with engine.connect() as conn:
        row = conn.execute(query, {"id": id}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"formula id {id} not found")

    return FormulaListItemOut(id=row.id, latex=row.latex)


@router.get("/formulas/{id}/graph", response_model=FormulaGraphOut)
def get_formula_graph(id: int) -> FormulaGraphOut:
    query = text(_SELECT_FORMULA_GRAPH)
    with engine.connect() as conn:
        row = conn.execute(query, {"id": id}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"formula id {id} not found")

    return FormulaGraphOut(**build_formula_graph_view(row))
