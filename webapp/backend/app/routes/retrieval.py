import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import bindparam, text

from ..db import RETRIEVAL_URL, engine
from ..render import build_segments, extract_formula_ids
from ..schemas import MultimodalOut, MultimodalResultOut, RetrievalOut, RetrievalResultOut
from .posts import _load_latex

router = APIRouter()

# The retrieval service returns gold.formula ids (not PG_GOLD_SCHEMA's), so the
# schema is fixed here.
_SELECT_GOLD_LATEX = text("SELECT id, latex FROM gold.formula WHERE id IN :ids").bindparams(
    bindparam("ids", expanding=True)
)

# The multimodal service returns silver.post_arqmath ids (not PG_SCHEMA's), so
# post text and formula LaTeX are always read from silver.
_SILVER_SCHEMA = "silver"
_SELECT_SILVER_POST_TEXT = text(
    f"SELECT silver_id, normalized_text_placeholders_formula_id FROM {_SILVER_SCHEMA}.post_arqmath "
    "WHERE silver_id IN :ids"
).bindparams(bindparam("ids", expanding=True))

_MAX_TOP_K = 200
_TIMEOUT_SECONDS = 120


def _call_retrieval_service(endpoint: str, params: dict) -> dict:
    url = f"{RETRIEVAL_URL}/{endpoint}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=_TIMEOUT_SECONDS) as res:
            return json.load(res)
    except HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Retrieval service error ({e.code}): {e.read().decode(errors='replace')}")
    except URLError as e:
        raise HTTPException(status_code=502, detail=f"Retrieval service unreachable at {RETRIEVAL_URL}: {e.reason}")


@router.get("/retrieval", response_model=RetrievalOut)
def retrieve_formulas(latex: str = Query(..., min_length=1), top_k: int = 20) -> RetrievalOut:
    top_k = max(1, min(top_k, _MAX_TOP_K))
    hits = _call_retrieval_service("retrieve_isolated_formula", {"latex": latex, "top_k": top_k})["results"]

    ids = [int(hit["formula_id"]) for hit in hits]
    latex_by_id: dict[int, str | None] = {}
    if ids:
        with engine.connect() as conn:
            latex_by_id = {row.id: row.latex for row in conn.execute(_SELECT_GOLD_LATEX, {"ids": ids})}

    results = [
        RetrievalResultOut(rank=rank, formula_id=fid, score=hit["score"], latex=latex_by_id.get(fid))
        for rank, (fid, hit) in enumerate(zip(ids, hits), start=1)
    ]
    return RetrievalOut(latex=latex, results=results)


@router.get("/multimodal_retrieval", response_model=MultimodalOut)
def retrieve_posts(query: str = Query(..., min_length=1), top_k: int = 20) -> MultimodalOut:
    """Text + $latex$ query -> ranked posts, with each post's text segmented like the Posts view."""
    top_k = max(1, min(top_k, _MAX_TOP_K))
    res = _call_retrieval_service("retrieve_multimodal_posts", {"query": query, "top_k": top_k})
    hits = res["results"]

    post_ids = [hit["silver_post_id"] for hit in hits]
    text_by_id: dict[int, str] = {}
    if post_ids:
        with engine.connect() as conn:
            rows = conn.execute(_SELECT_SILVER_POST_TEXT, {"ids": post_ids}).fetchall()
        text_by_id = {row.silver_id: row.normalized_text_placeholders_formula_id or "" for row in rows}

    formula_ids: set[int] = set()
    for placeholder_text in text_by_id.values():
        formula_ids.update(extract_formula_ids(placeholder_text))
    id_to_latex = _load_latex(formula_ids, schema=_SILVER_SCHEMA)

    results = [
        MultimodalResultOut(
            rank=rank,
            content=(
                build_segments(text_by_id[hit["silver_post_id"]], id_to_latex)
                if hit["silver_post_id"] in text_by_id
                else None
            ),
            **hit,
        )
        for rank, hit in enumerate(hits, start=1)
    ]
    return MultimodalOut(
        query=query,
        formulas=res.get("formulas", []),
        text_query=res.get("text_query", ""),
        results=results,
    )
