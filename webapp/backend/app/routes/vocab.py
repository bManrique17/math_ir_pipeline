from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..db import engine
from ..schemas import VocabOut

router = APIRouter()

# public.vocab / public.dataset are not schema-prefixed: they live in public
# regardless of PG_SCHEMA / PG_GOLD_SCHEMA.
_SELECT_VOCAB = (
    "SELECT v.id, v.dataset_id, d.name AS dataset_name, v.comments, "
    "v.slt, v.opt, v.slt_inverted, v.opt_inverted, v.slt_count, v.opt_count, "
    "v.slt_edge, v.opt_edge, v.slt_edge_inverted, v.opt_edge_inverted, "
    "v.slt_edge_count, v.opt_edge_count "
    "FROM public.vocab v "
    "LEFT JOIN public.dataset d ON d.id = v.dataset_id "
    "WHERE v.id = :id"
)


@router.get("/vocab/{id}", response_model=VocabOut)
def get_vocab(id: int) -> VocabOut:
    with engine.connect() as conn:
        row = conn.execute(text(_SELECT_VOCAB), {"id": id}).mappings().fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"vocab id {id} not found")

    return VocabOut(**row)
