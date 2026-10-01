import { useState } from "react";

import { fetchVocabById } from "../api";
import SearchBar from "./SearchBar";

// One vocab (id -> token) joined with its counts (token -> occurrences), in id order.
function VocabTable({ title, vocab, count }) {
  const [filter, setFilter] = useState("");

  if (!vocab) {
    return (
      <div className="card h-100">
        <div className="card-header fw-semibold">{title}</div>
        <div className="card-body text-muted fst-italic">Not available for this vocab</div>
      </div>
    );
  }

  const rows = Object.entries(vocab)
    .map(([id, token]) => ({ id: Number(id), token, count: count?.[token] }))
    .sort((a, b) => a.id - b.id);
  const needle = filter.trim().toLowerCase();
  const shown = needle ? rows.filter((r) => r.token.toLowerCase().includes(needle)) : rows;

  return (
    <div className="card h-100">
      <div className="card-header d-flex justify-content-between align-items-center">
        <span className="fw-semibold">{title}</span>
        <span className="text-muted small">{rows.length} tokens</span>
      </div>
      <div className="card-body">
        <input
          type="text"
          className="form-control form-control-sm mb-2"
          placeholder="Filter tokens"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <div style={{ maxHeight: "400px", overflowY: "auto" }}>
          <table className="table table-sm table-bordered align-middle mb-0">
            <thead className="sticky-top">
              <tr>
                <th>ID</th>
                <th>Token</th>
                <th className="text-end">Count</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>
                    <code>{r.token}</code>
                  </td>
                  <td className="text-end">{r.count ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function VocabView() {
  const [vocab, setVocab] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (id) => {
    setLoading(true);
    setError(null);
    try {
      setVocab(await fetchVocabById(id));
    } catch (e) {
      setError(e.message);
      setVocab(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setVocab(null);
    setError(null);
  };

  return (
    <div className="container py-4">
      <h1 className="mb-4">Vocab</h1>

      <div className="mb-4">
        <SearchBar
          placeholder="Search by vocab id"
          clearLabel="Clear"
          onSearch={handleSearch}
          onClear={handleClear}
          searchActive={vocab !== null || error !== null}
        />
      </div>

      {loading && <p className="text-muted">Loading...</p>}
      {error && <div className="alert alert-danger">{error}</div>}

      {vocab && (
        <>
          <dl className="row mb-4">
            <dt className="col-sm-2">Vocab id</dt>
            <dd className="col-sm-10">{vocab.id}</dd>
            <dt className="col-sm-2">Dataset</dt>
            <dd className="col-sm-10">
              {vocab.dataset_id}
              {vocab.dataset_name && <span className="text-muted"> ({vocab.dataset_name})</span>}
            </dd>
            <dt className="col-sm-2">Comments</dt>
            <dd className="col-sm-10">
              {vocab.comments || <span className="text-muted fst-italic">none</span>}
            </dd>
          </dl>

          <div className="row g-4">
            <div className="col-lg-6">
              <VocabTable title="SLT nodes" vocab={vocab.slt} count={vocab.slt_count} />
            </div>
            <div className="col-lg-6">
              <VocabTable title="OPT nodes" vocab={vocab.opt} count={vocab.opt_count} />
            </div>
            <div className="col-lg-6">
              <VocabTable title="SLT edges" vocab={vocab.slt_edge} count={vocab.slt_edge_count} />
            </div>
            <div className="col-lg-6">
              <VocabTable title="OPT edges" vocab={vocab.opt_edge} count={vocab.opt_edge_count} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
