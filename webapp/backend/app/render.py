import re

import graphviz

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


def _truncate(text: str, max_len: int = 60) -> str:
    return text if len(text) <= max_len else text[: max_len] + "…"


def _dict_to_svg(data: dict | None) -> str | None:
    """Render a stored nx.node_link_data(...) dict to an SVG string via graphviz.

    Reads `nodes`/`links`(or `edges`) straight off the dict rather than round-tripping
    through nx.node_link_graph -- the edges key name is networkx version-dependent
    (see ETL/etl/annotate_opt_formulas.py for the same issue on the write side), so
    this sidesteps it entirely.

    Every structural node gets the same flat style regardless of its symbol type
    (no more V/N/F/... color coding); the only visual distinction is annotation
    nodes (type "ANNOTATION") vs. everything else, mirroring DEBUG/viz_opt.py.
    Node labels are the raw, unsplit tag (e.g. "V!x"), not the parsed symbol/type.
    """
    if not data:
        return None

    nodes = data.get("nodes", [])
    if not nodes:
        return None
    edges = data.get("links", data.get("edges", []))

    dot = graphviz.Digraph(graph_attr={"rankdir": "TB", "fontsize": "10"})
    for node in nodes:
        node_id = str(node["id"])
        if node.get("type") == "ANNOTATION":
            label = _truncate(str(node.get("label") or node_id), 60)
            dot.node(
                node_id,
                label=label,
                shape="box",
                style="filled",
                fillcolor="#fffacd",
                fontsize="9",
                width="1.5",
            )
        else:
            label = node.get("original_tag") or node.get("label") or node_id
            dot.node(node_id, label=str(label), shape="ellipse", style="filled", fillcolor="#add8e6", fontsize="9")

    for edge in edges:
        dot.edge(str(edge["source"]), str(edge["target"]), label=str(edge.get("label", "")), fontsize="8")

    svg = dot.pipe(format="svg").decode("utf-8")
    return svg[svg.index("<svg") :]


def build_formula_graph_view(row) -> dict:
    """Build the {opt, slt} graph payload for a single formula occurrence.

    OPT prefers the post-context-annotated graph (formula_arqmath.opt_nx_dict_annotated);
    falls back to the raw gold OPT tree when no annotation pass has run yet (or
    nothing matched) for this occurrence. SLT has no annotated variant, so it is
    always the raw gold tree.
    """
    annotated_opt = getattr(row, "opt_nx_dict_annotated", None)
    raw_opt = getattr(row, "opt_nx_dict", None)
    raw_slt = getattr(row, "slt_nx_dict", None)

    opt_source = annotated_opt if annotated_opt is not None else raw_opt
    opt_svg = _dict_to_svg(opt_source)
    slt_svg = _dict_to_svg(raw_slt)

    return {
        "id": row.id,
        "latex": row.latex,
        "opt": {
            "available": opt_svg is not None,
            "annotated": annotated_opt is not None,
            "svg": opt_svg,
        },
        "slt": {
            "available": slt_svg is not None,
            "annotated": False,
            "svg": slt_svg,
        },
    }
