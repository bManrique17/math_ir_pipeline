from typing import Literal, Union

from pydantic import BaseModel


class TextSegment(BaseModel):
    type: Literal["text"] = "text"
    text: str


class FormulaSegment(BaseModel):
    type: Literal["formula"] = "formula"
    id: int
    latex: str


Segment = Union[TextSegment, FormulaSegment]


class FormulaOut(BaseModel):
    id: int
    latex: str


class PostOut(BaseModel):
    silver_id: int
    content: list[Segment]
    formulas: list[FormulaOut]
    descriptors: dict[str, list[str]]


class PostListOut(BaseModel):
    items: list[PostOut]
    has_more: bool


class FormulaGraphSvgOut(BaseModel):
    available: bool
    annotated: bool = False
    svg: str | None = None


class FormulaGraphOut(BaseModel):
    id: int
    latex: str | None
    opt: FormulaGraphSvgOut
    slt: FormulaGraphSvgOut


class FormulaListItemOut(BaseModel):
    id: int
    latex: str | None = None


class FormulaListOut(BaseModel):
    items: list[FormulaListItemOut]
    has_more: bool


class VocabOut(BaseModel):
    id: int
    dataset_id: int
    dataset_name: str | None = None
    comments: str | None = None
    slt: dict[str, str] | None = None
    opt: dict[str, str] | None = None
    slt_inverted: dict[str, int] | None = None
    opt_inverted: dict[str, int] | None = None
    slt_count: dict[str, int] | None = None
    opt_count: dict[str, int] | None = None
    slt_edge: dict[str, str] | None = None
    opt_edge: dict[str, str] | None = None
    slt_edge_inverted: dict[str, int] | None = None
    opt_edge_inverted: dict[str, int] | None = None
    slt_edge_count: dict[str, int] | None = None
    opt_edge_count: dict[str, int] | None = None


class RetrievalResultOut(BaseModel):
    rank: int
    formula_id: int
    score: float
    latex: str | None = None


class RetrievalOut(BaseModel):
    latex: str
    results: list[RetrievalResultOut]


class MultimodalResultOut(BaseModel):
    rank: int
    silver_post_id: int
    post_id: int
    post_type_id: int | None = None
    score: float
    formula_score: float | None = None
    text_score: float | None = None
    text: str | None = None
    # Post text as segments (formulas resolved to LaTeX), like PostOut.content;
    # None when the post is not in silver.post_arqmath.
    content: list[Segment] | None = None


class MultimodalOut(BaseModel):
    query: str
    formulas: list[str]
    text_query: str
    results: list[MultimodalResultOut]
