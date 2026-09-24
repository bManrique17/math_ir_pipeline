from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..db import PG_SCHEMA, engine
from ..render import build_post_view, extract_formula_ids
from ..schemas import PostListOut, PostOut

router = APIRouter()

_SELECT_POST = (
    "SELECT silver_id, normalized_text_placeholders_formula_id, formula_descriptors "
    f"FROM {PG_SCHEMA}.post_arqmath"
)

_MAX_LIMIT = 100


def _load_latex(ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    query = text(f"SELECT id, latex FROM {PG_SCHEMA}.formula_arqmath WHERE id = ANY(:ids)")
    with engine.connect() as conn:
        rows = conn.execute(query, {"ids": list(ids)}).fetchall()
    return {row.id: row.latex for row in rows}


@router.get("/posts", response_model=PostListOut)
def list_posts(offset: int = 0, limit: int = 10) -> PostListOut:
    limit = max(1, min(limit, _MAX_LIMIT))
    query = text(f"{_SELECT_POST} ORDER BY silver_id LIMIT :limit OFFSET :offset")
    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit + 1, "offset": offset}).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    ids_needed: set[int] = set()
    for row in rows:
        ids_needed.update(extract_formula_ids(row.normalized_text_placeholders_formula_id or ""))
    id_to_latex = _load_latex(ids_needed)

    items = [build_post_view(row, id_to_latex) for row in rows]
    return PostListOut(items=items, has_more=has_more)


@router.get("/posts/{silver_id}", response_model=PostOut)
def get_post(silver_id: int) -> PostOut:
    query = text(f"{_SELECT_POST} WHERE silver_id = :sid")
    with engine.connect() as conn:
        row = conn.execute(query, {"sid": silver_id}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"silver_id {silver_id} not found")

    ids_needed = set(extract_formula_ids(row.normalized_text_placeholders_formula_id or ""))
    id_to_latex = _load_latex(ids_needed)

    return PostOut(**build_post_view(row, id_to_latex))
