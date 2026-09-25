"""Build post-context-aware annotated OPT graphs.

For every post, each formula referenced in it gets an annotated copy of its
gold OPT (content-MathML operator) tree: a "text" node is attached wherever a
node's subtree is *exactly* the same (same labels, same child order, with
commutative/"U!" operators treated as unordered) as the whole tree of some
formula in that same post that has descriptor sentences
(post_arqmath.formula_descriptors). This covers, in one pass:

  - direct annotation: a formula's own root always matches its own sentences
  - propagation: any subexpression elsewhere in the post that is structurally
    identical to an annotated formula inherits its sentence(s) too

e.g. if formula "x^2" (post A) is annotated "always positive in real numbers",
and the same post also contains "x^2+y+c", the "x^2" subtree inside that
second formula's OPT tree gets the same text node attached.

Written into silver.formula_arqmath.opt_nx_dict_annotated, one row per raw
formula occurrence (not per gold/visual_id formula), because the same gold
formula can appear in different posts with different sibling formulas and
sentences, and therefore get a different annotated graph each time.
"""

import json
import re
from collections import defaultdict

import networkx as nx
import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine
from tqdm import tqdm

SILVER_FORMULA_TABLE = "formula_arqmath"
SILVER_POST_TABLE = "post_arqmath"
GOLD_FORMULA_TABLE = "formula"

_FORMULA_RE = re.compile(r"\[(\d+)\]")


def _extract_formula_ids(text_placeholders: str | None) -> list[int]:
    """Distinct raw formula ids referenced in a post's placeholder text, in first-seen order."""
    if not text_placeholders:
        return []
    seen: list[int] = []
    seen_set: set[int] = set()
    for match in _FORMULA_RE.finditer(text_placeholders):
        fid = int(match.group(1))
        if fid not in seen_set:
            seen_set.add(fid)
            seen.append(fid)
    return seen


def _load_formula_id_to_fk_gold(engine: Engine, silver_schema: str) -> dict[int, int]:
    query = text(f"SELECT id, fk_gold_formula FROM {silver_schema}.{SILVER_FORMULA_TABLE}")
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    df = df.dropna(subset=["fk_gold_formula"])
    return dict(zip(df["id"].astype(int), df["fk_gold_formula"].astype(int)))


def _fetch_opt_trees(engine: Engine, gold_schema: str, gold_ids: set[int]) -> dict[int, dict]:
    if not gold_ids:
        return {}
    query = text(f"SELECT id, opt_nx_dict FROM {gold_schema}.{GOLD_FORMULA_TABLE} WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"ids": list(gold_ids)}).fetchall()
    return {row.id: row.opt_nx_dict for row in rows if row.opt_nx_dict is not None}


def _canonical_signatures(graph: nx.DiGraph, root: int = 0) -> dict[int, str]:
    """Bottom-up canonical signature per node.

    Children are ordered by their edge label (argument position), except under
    a "U" (commutative) node where all edge labels are 0 and child signatures
    are instead sorted lexicographically, so e.g. "x+2" and "2+x" canonicalize
    the same way.
    """
    if graph.number_of_nodes() == 0:
        return {}

    # Iterative DFS discovery order: for a tree, a child is always discovered
    # strictly after its parent, so processing in reverse guarantees every
    # child's signature is already computed before its parent's.
    discovery_order: list[int] = []
    stack = [root]
    visited: set[int] = set()
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        discovery_order.append(node)
        stack.extend(v for _, v in graph.out_edges(node))

    signatures: dict[int, str] = {}
    for node in reversed(discovery_order):
        data = graph.nodes[node]
        ordered_children = sorted(
            graph.out_edges(node, data=True),
            key=lambda e: e[2].get("label", 0),
        )
        child_sigs = [signatures[v] for _, v, _ in ordered_children]
        if data.get("type") == "U":
            child_sigs = sorted(child_sigs)
        signatures[node] = f"{data.get('label')}|{data.get('type')}(" + ",".join(child_sigs) + ")"

    return signatures


def _annotate_post_formulas(
    formula_ids: list[int],
    formula_id_to_gold: dict[int, int],
    gold_trees: dict[int, dict],
    descriptors: dict,
) -> dict[int, dict]:
    """Return {raw_formula_id: annotated opt_nx_dict} for every formula in the post with a resolvable tree."""

    graphs: dict[int, nx.DiGraph] = {}
    signatures: dict[int, dict[int, str]] = {}
    for fid in formula_ids:
        gold_id = formula_id_to_gold.get(fid)
        if gold_id is None:
            continue
        opt_dict = gold_trees.get(gold_id)
        if opt_dict is None:
            continue
        # No `edges=` override: match whatever key name this networkx version's
        # node_link_data (used both by gold_formulas_arqmath.py and below) defaults to.
        graph = nx.node_link_graph(opt_dict, directed=True, multigraph=False)
        if graph.number_of_nodes() == 0:
            continue
        graphs[fid] = graph
        signatures[fid] = _canonical_signatures(graph)

    if not graphs:
        return {}

    # signature -> unique sentences contributed by any formula whose ROOT matches it,
    # paired with the formula id that contributed each sentence (for traceability)
    sig_to_sentences: dict[str, list[str]] = defaultdict(list)
    sig_to_sources: dict[str, list[int]] = defaultdict(list)
    for fid, graph in graphs.items():
        sentences = (descriptors or {}).get(str(fid)) or []
        root_sig = signatures[fid].get(0)
        if root_sig is None:
            continue
        for sentence in sentences:
            if sentence not in sig_to_sentences[root_sig]:
                sig_to_sentences[root_sig].append(sentence)
                sig_to_sources[root_sig].append(fid)

    annotated: dict[int, dict] = {}
    for fid, graph in graphs.items():
        working = graph.copy()
        next_id = max(working.nodes) + 1
        for node, sig in signatures[fid].items():
            sentences = sig_to_sentences.get(sig)
            if not sentences:
                continue
            for sentence, source_fid in zip(sentences, sig_to_sources[sig]):
                working.add_node(
                    next_id,
                    original_tag=None,
                    label=sentence,
                    type="ANNOTATION",
                    source_formula_id=source_fid,
                )
                working.add_edge(next_id, node, label="annotation", edge_type="annotation")
                next_id += 1
        # Always emit a value once a tree was resolvable, even if nothing matched
        # (opt_nx_dict_annotated then equals opt_nx_dict): NULL keeps meaning
        # "no gold OPT tree could be resolved for this occurrence".
        annotated[fid] = nx.node_link_data(working)

    return annotated


def build_opt_annotations(
    engine: Engine,
    silver_schema: str,
    gold_schema: str,
    chunk_size: int = 50_000,
) -> int:
    formula_id_to_gold = _load_formula_id_to_fk_gold(engine, silver_schema)
    print(f">>Loaded {len(formula_id_to_gold)} formula id -> gold id mappings")

    select_sql = text(
        f"SELECT silver_id, normalized_text_placeholders_formula_id, formula_descriptors "
        f"FROM {silver_schema}.{SILVER_POST_TABLE} "
        f"WHERE normalized_text_placeholders_formula_id IS NOT NULL"
    )
    update_sql = text(
        f"UPDATE {silver_schema}.{SILVER_FORMULA_TABLE} "
        f"SET opt_nx_dict_annotated = CAST(:val AS jsonb) "
        f"WHERE id = :fid"
    )

    total_written = 0
    with engine.connect() as read_conn:
        for chunk in tqdm(
            pd.read_sql(select_sql, read_conn, chunksize=chunk_size),
            desc="annotate_opt_formulas",
            unit="chunk",
        ):
            chunk_formula_ids = {
                row.silver_id: _extract_formula_ids(row.normalized_text_placeholders_formula_id)
                for row in chunk.itertuples()
            }

            gold_ids_needed = {
                formula_id_to_gold[fid]
                for fids in chunk_formula_ids.values()
                for fid in fids
                if fid in formula_id_to_gold
            }
            gold_trees = _fetch_opt_trees(engine, gold_schema, gold_ids_needed)

            write_buffer: list[dict] = []
            for row in chunk.itertuples():
                fids = chunk_formula_ids[row.silver_id]
                if not fids:
                    continue
                annotated = _annotate_post_formulas(
                    fids, formula_id_to_gold, gold_trees, row.formula_descriptors
                )
                write_buffer.extend({"val": json.dumps(opt_dict), "fid": fid} for fid, opt_dict in annotated.items())

            if write_buffer:
                with engine.begin() as write_conn:
                    write_conn.execute(update_sql, write_buffer)
                total_written += len(write_buffer)

    return total_written
