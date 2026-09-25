import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { fetchFormulaGraph } from "../api";
import { useMathJaxTypeset } from "../hooks/useMathJax";
import FormulaGraphView from "./FormulaGraphView";

export default function FormulaGraphPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const latexRef = useMathJaxTypeset([data]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    fetchFormulaGraph(id)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="container py-4">
      <button
        type="button"
        className="btn btn-outline-secondary btn-sm mb-3"
        onClick={() => navigate(-1)}
      >
        &larr; Back
      </button>

      <h1 className="mb-3">Formula {id}</h1>

      {loading && <p className="text-muted">Loading...</p>}
      {error && <div className="alert alert-danger">{error}</div>}

      {data && (
        <>
          <div ref={latexRef} className="mb-4 fs-4">
            {data.latex ? `\\(${data.latex}\\)` : <span className="text-muted fst-italic">(no latex)</span>}
          </div>

          <div className="row g-4">
            <div className="col-lg-6">
              <FormulaGraphView title="Operator tree (OPT)" graph={data.opt} />
            </div>
            <div className="col-lg-6">
              <FormulaGraphView title="Symbol layout tree (SLT)" graph={data.slt} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
