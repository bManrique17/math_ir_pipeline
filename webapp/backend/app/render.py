import re

_PLACEHOLDER_RE = re.compile(r"\[(\d+)\]")


def extract_formula_ids(text: str) -> list[int]:
    """Unique formula ids referenced in text, in order of first appearance."""
    seen: list[int] = []
    seen_set: set[int] = set()
    for m in _PLACEHOLDER_RE.finditer(text):
        fid = int(m.group(1))
        if fid not in seen_set:
            seen_set.add(fid)
            seen.append(fid)
    return seen


def build_segments(text: str, id_to_latex: dict[int, str]) -> list[dict]:
    """Split text into {type: text|formula} segments for the frontend to render."""
    segments: list[dict] = []
    pos = 0
    for m in _PLACEHOLDER_RE.finditer(text):
        if m.start() > pos:
            segments.append({"type": "text", "text": text[pos:m.start()]})
        fid = int(m.group(1))
        latex = id_to_latex.get(fid)
        if latex is not None:
            segments.append({"type": "formula", "id": fid, "latex": latex})
        else:
            segments.append({"type": "text", "text": m.group(0)})
        pos = m.end()
    if pos < len(text):
        segments.append({"type": "text", "text": text[pos:]})
    return segments


def build_post_view(row, id_to_latex: dict[int, str]) -> dict:
    raw_text = row.normalized_text_placeholders_formula_id or ""
    ids = extract_formula_ids(raw_text)
    return {
        "silver_id": row.silver_id,
        "content": build_segments(raw_text, id_to_latex),
        "formulas": [{"id": fid, "latex": id_to_latex[fid]} for fid in ids if fid in id_to_latex],
        "descriptors": row.formula_descriptors or {},
    }
