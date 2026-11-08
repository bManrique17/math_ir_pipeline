import { useState } from "react";
import { Link } from "react-router-dom";

import { fetchAnnotatedRetrieval } from "../api";
import { useMathJaxTypeset } from "../hooks/useMathJax";

const DEFAULT_TOP_K = 20;

function SentenceList({ sentences }) {
  if (!sentences || sentences.length === 0) {
    return <span className="text-muted fst-italic">none</span>;
  }
  return (
    <ul className="mb-0 ps-3">
      {sentences.map((s, i) => (
        <li key={i}>{s}</li>
      ))}
    </ul>
  );
}

export default function AnnotatedRetrievalView() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(DEFAULT_TOP_K);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const resultsRef = useMathJaxTypeset([data]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const q = query.trim();
    if (q === "") return;
    setLoading(true);
    setError(null);
    try {
      setData(await fetchAnnotatedRetrieval(q, topK || DEFAULT_TOP_K));
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container py-4">
      <h1 className="mb-4">Annotated formula retrieval</h1>

      <form className="d-flex align-items-center gap-2 mb-4" onSubmit={handleSubmit}>
        <input
          type="text"
          className="form-control font-monospace"
          placeholder="text with $latex$ formulas"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="text-nowrap small text-muted" htmlFor="annotated-retrieval-top-k">
          top k
        </label>
        <input
          id="annotated-retrieval-top-k"
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

      <div ref={resultsRef}>
        {data && (
          <>
            <h5>Query formulas</h5>
            {data.query_formulas.length > 0 ? (
              <table className="table table-sm table-bordered align-middle mb-4">
                <thead>
                  <tr>
                    <th>Formula</th>
                    <th>Descriptors</th>
                    {/* <th>Descriptors (original post)</th> */}
                    {/* <th>Descriptors (inherited)</th> */}
                  </tr>
                </thead>
                <tbody>
                  {data.query_formulas.map((f, i) => (
                    <tr key={i}>
                      <td>{`\\(${f.latex}\\)`}</td>
                      <td>
                        <SentenceList sentences={f.descriptors} />
                      </td>
                      {/* <td>
                        <SentenceList sentences={f.annotations} />
                      </td> */}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-muted fst-italic">none</p>
            )}

            <p className="text-muted">{data.results.length} results</p>
            {data.results.length > 0 && (
              <table className="table table-sm table-bordered align-middle">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>silver id</th>
                    <th>Score</th>
                    <th>Formula</th>
                    <th>Annotations</th>
                    <th>Post</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((r) => (
                    <tr key={r.formula_id}>
                      <td>{r.rank}</td>
                      <td>{r.silver_formula_id}</td>
                      <td>{r.score.toFixed(4)}</td>
                      <td>
                        {r.latex ? `\\(${r.latex}\\)` : <span className="text-muted fst-italic">(no latex)</span>}
                      </td>
                      <td>
                        <SentenceList sentences={r.annotations} />
                      </td>
                      <td className="small text-nowrap">
                        {r.silver_post_id != null ? (
                          <>
                            <div>silver_id: {r.silver_post_id}</div>
                            <div>post_id: {r.post_id ?? "?"}</div>
                          </>
                        ) : (
                          <span className="text-muted fst-italic">none</span>
                        )}
                      </td>
                      <td>
                        <Link to={`/silver_formula/${r.silver_formula_id}`} className="link-secondary small text-nowrap">
                          View graph
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </div>
  );
}
