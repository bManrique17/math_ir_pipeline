import { useState } from "react";

import { fetchMultimodalRetrieval } from "../api";
import { useMathJaxTypeset } from "../hooks/useMathJax";
import PostText from "./PostText";

const DEFAULT_TOP_K = 20;
// Posts longer than this (in characters, LaTeX included) start collapsed to COLLAPSED_HEIGHT.
const PREVIEW_CHARS = 400;
const COLLAPSED_HEIGHT = "7.5em";
// ARQMath PostTypeId
const POST_TYPES = { 1: "Question", 2: "Answer" };

// result.content is the post as text/formula segments (rendered like the Posts view);
// it is null when the post is not in silver.post_arqmath, in which case the service's
// plain text (formulas as raw, undelimited LaTeX) is shown instead.
function PostResult({ result }) {
  const [expanded, setExpanded] = useState(false);
  const text = result.text ?? "";
  const length = result.content
    ? result.content.reduce((n, seg) => n + (seg.type === "formula" ? seg.latex.length : seg.text.length), 0)
    : text.length;
  const collapsible = length > PREVIEW_CHARS;

  return (
    <div className="card mb-3">
      <div className="card-header d-flex flex-wrap gap-3 align-items-center small">
        <strong>#{result.rank}</strong>
        <span>silver_id: {result.silver_post_id}</span>
        <span>post_id: {result.post_id}</span>
        {result.post_type_id != null && (
          <span className="badge text-bg-secondary">
            {POST_TYPES[result.post_type_id] ?? `type ${result.post_type_id}`}
          </span>
        )}
        <span className="ms-auto text-muted">
          score {result.score.toFixed(4)}
          {result.formula_score != null && <> · formula {result.formula_score.toFixed(4)}</>}
          {result.text_score != null && <> · text {result.text_score.toFixed(4)}</>}
        </span>
      </div>
      <div className="card-body">
        <div style={collapsible && !expanded ? { maxHeight: COLLAPSED_HEIGHT, overflow: "hidden" } : undefined}>
          {result.content ? (
            <PostText content={result.content} />
          ) : text ? (
            <p className="mb-0" style={{ whiteSpace: "pre-wrap" }}>
              {text}
            </p>
          ) : (
            <span className="text-muted fst-italic">(no text)</span>
          )}
        </div>
        {collapsible && (
          <button type="button" className="btn btn-link btn-sm p-0 mt-1" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function MultimodalRetrievalView() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(DEFAULT_TOP_K);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const parsedRef = useMathJaxTypeset([data]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const q = query.trim();
    if (q === "") return;
    setLoading(true);
    setError(null);
    try {
      setData(await fetchMultimodalRetrieval(q, topK || DEFAULT_TOP_K));
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container py-4">
      <h1 className="mb-4">Multimodal retrieval</h1>

      <form className="d-flex align-items-center gap-2 mb-4" onSubmit={handleSubmit}>
        <input
          type="text"
          className="form-control font-monospace"
          placeholder="text with $latex$ formulas"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="text-nowrap small text-muted" htmlFor="multimodal-top-k">
          top k
        </label>
        <input
          id="multimodal-top-k"
          type="number"
          min={1}
          className="form-control"
          style={{ maxWidth: "90px" }}
          value={topK}
          onChange={(e) => setTopK(Number(e.target.value))}
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <div className="alert alert-danger">{error}</div>}

      {data && (
        <>
          <dl ref={parsedRef} className="row mb-4">
            <dt className="col-sm-2">Formulas</dt>
            <dd className="col-sm-10">
              {data.formulas.length > 0 ? (
                data.formulas.map((f, i) => (
                  <span key={i} className="me-4">{`\\(${f}\\)`}</span>
                ))
              ) : (
                <span className="text-muted fst-italic">none</span>
              )}
            </dd>
            <dt className="col-sm-2">Text</dt>
            <dd className="col-sm-10">
              {data.text_query || <span className="text-muted fst-italic">none</span>}
            </dd>
          </dl>

          <p className="text-muted">{data.results.length} results</p>
          {data.results.map((r) => (
            <PostResult key={r.silver_post_id} result={r} />
          ))}
        </>
      )}
    </div>
  );
}
