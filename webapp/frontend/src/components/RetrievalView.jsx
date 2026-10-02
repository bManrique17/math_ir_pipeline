import { useState } from "react";
import { Link } from "react-router-dom";

import { fetchRetrieval } from "../api";
import { useMathJaxTypeset } from "../hooks/useMathJax";

const DEFAULT_TOP_K = 20;

export default function RetrievalView() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(DEFAULT_TOP_K);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const resultsRef = useMathJaxTypeset([data]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const latex = query.trim();
    if (latex === "") return;
    setLoading(true);
    setError(null);
    try {
      setData(await fetchRetrieval(latex, topK || DEFAULT_TOP_K));
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container py-4">
      <h1 className="mb-4">Formula retrieval</h1>

      <form className="d-flex align-items-center gap-2 mb-4" onSubmit={handleSubmit}>
        <input
          type="text"
          className="form-control font-monospace"
          placeholder="latex"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="text-nowrap small text-muted" htmlFor="retrieval-top-k">
          top k
        </label>
        <input
          id="retrieval-top-k"
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
            <h3 className="text-muted">
              {`\\(${data.latex}\\)`}
            </h3>
            {data.results.length > 0 && (
              <table className="table table-sm table-bordered align-middle">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>id</th>
                    <th>Score</th>
                    <th>Formula</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((r) => (
                    <tr key={r.formula_id}>
                      <td>{r.rank}</td>
                      <td>{r.formula_id}</td>
                      <td>{r.score.toFixed(4)}</td>
                      <td>
                        {r.latex ? (
                          `\\(${r.latex}\\)`
                        ) : (
                          <span className="text-muted fst-italic">(not in gold.formula)</span>
                        )}
                      </td>
                      <td>
                        <Link to={`/gold_formula/${r.formula_id}`} className="link-secondary small">
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
