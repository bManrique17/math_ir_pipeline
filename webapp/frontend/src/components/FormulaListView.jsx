import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { fetchFormulaById, fetchFormulas, fetchPostBySilverId } from "../api";
import { useMathJaxTypeset } from "../hooks/useMathJax";
import SearchBar from "./SearchBar";

const PAGE_SIZE = 20;

export default function FormulaListView() {
  const [formulas, setFormulas] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // "list": paginated, all formulas. "formula": a single formula id search.
  // "post": formulas referenced by one post id.
  const [mode, setMode] = useState("list");
  const [contextLabel, setContextLabel] = useState(null);
  const initialized = useRef(false);
  const tableRef = useMathJaxTypeset([formulas]);

  const loadPage = useCallback(async (currentOffset) => {
    setLoading(true);
    setError(null);
    try {
      const { items, has_more } = await fetchFormulas(currentOffset, PAGE_SIZE);
      setFormulas((prev) => [...prev, ...items]);
      setOffset(currentOffset + PAGE_SIZE);
      setHasMore(has_more);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    loadPage(0);
  }, [loadPage]);

  const handleSearchFormula = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const formula = await fetchFormulaById(id);
      setFormulas([formula]);
      setMode("formula");
      setContextLabel(`formula id ${id}`);
      setHasMore(false);
    } catch (e) {
      setError(e.message);
      setFormulas([]);
      setMode("formula");
    } finally {
      setLoading(false);
    }
  };

  const handleFilterByPost = async (postId) => {
    setLoading(true);
    setError(null);
    try {
      const post = await fetchPostBySilverId(postId);
      setFormulas(post.formulas);
      setMode("post");
      setContextLabel(`post silver_id ${postId}`);
      setHasMore(false);
    } catch (e) {
      setError(e.message);
      setFormulas([]);
      setMode("post");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setError(null);
    setFormulas([]);
    setOffset(0);
    setHasMore(true);
    setMode("list");
    setContextLabel(null);
    loadPage(0);
  };

  const searchActive = mode !== "list";

  return (
    <div className="container py-4">
      <h1 className="mb-4">Formulas</h1>

      <div className="d-flex flex-column gap-2 mb-4">
        <SearchBar
          placeholder="Search by formula id"
          clearLabel="Show all formulas"
          onSearch={handleSearchFormula}
          onClear={handleClear}
          searchActive={searchActive}
        />
        <SearchBar
          placeholder="Filter by post id"
          clearLabel="Show all formulas"
          onSearch={handleFilterByPost}
          onClear={handleClear}
          searchActive={searchActive}
        />
      </div>
      
      {error && <div className="alert alert-danger">{error}</div>}

      {formulas.length === 0 && !loading && !error ? (
        <p className="text-muted fst-italic">No formulas</p>
      ) : (
        formulas.length > 0 && (
          <table ref={tableRef} className="table table-sm table-bordered align-middle">
            <thead>
              <tr>
                <th>ID</th>
                <th>Formula</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {formulas.map((f) => (
                <tr key={f.id}>
                  <td>{f.id}</td>
                  <td>
                    {f.latex ? (
                      `\\(${f.latex}\\)`
                    ) : (
                      <span className="text-muted fst-italic">(no latex)</span>
                    )}
                  </td>
                  <td>
                    <Link to={`/formula/${f.id}`} className="link-secondary small">
                      View graph
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}

      {mode === "list" && (
        <div className="text-center my-4">
          {hasMore ? (
            <button
              className="btn btn-outline-primary"
              disabled={loading}
              onClick={() => loadPage(offset)}
            >
              {loading ? "Loading..." : "Show more"}
            </button>
          ) : (
            formulas.length > 0 && <p className="text-muted">No more formulas</p>
          )}
        </div>
      )}
    </div>
  );
}
