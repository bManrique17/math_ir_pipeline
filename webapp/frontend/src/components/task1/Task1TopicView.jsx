import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  CollapsibleMath,
  CoverageWarning,
  Formula,
  MathText,
  MetricCard,
  RELEVANCE,
  RelevanceBadge,
  fmt,
  formatDuration,
  loadTopicResults,
  RetrieverPicker,
  retrieverInfo,
  retrieverLabel,
  settingsToParams,
  useElapsed,
  useTask1Settings,
} from "./shared";

const PAGE_SIZES = [25, 50, 100];

function modality(r) {
  const f = r.formula_score != null;
  const t = r.text_score != null;
  if (f && t) return { key: "both", label: "formula + text", cls: "text-bg-dark" };
  if (f) return { key: "formula", label: "formula", cls: "bg-info-subtle text-info-emphasis" };
  if (t) return { key: "text", label: "text", cls: "bg-light text-dark border" };
  return { key: "none", label: "?", cls: "text-bg-light" };
}

// Where the judged answers fall over ranks 1..top_k: one tick per judged answer, colored by relevance.
function RankStrip({ results, topK, onPick }) {
  const judged = results.filter((r) => r.relevance != null);
  return (
    <div className="mb-3">
      <div className="d-flex justify-content-between small text-muted mb-1">
        {/* <span>Judged answers by rank (click to jump)</span> */}
        <span className="d-flex gap-2">
          {[3, 2, 1, 0].map((rel) => (
            <span key={rel}>
              <span className="d-inline-block rounded-1 me-1" style={{ width: 10, height: 10, background: RELEVANCE[rel].color }} />
              {rel}
            </span>
          ))}
        </span>
      </div>
      <svg
        viewBox={`0 0 ${topK} 24`}
        preserveAspectRatio="none"
        className="w-100 border rounded bg-body-tertiary"
        style={{ height: 28, display: "block" }}
      >
        {judged.map((r) => (
          <rect
            key={r.rank}
            x={r.rank - 1}
            y={r.relevance >= 2 ? 0 : 8}
            width={Math.max(1, topK / 400)}
            height={r.relevance >= 2 ? 24 : 16}
            fill={RELEVANCE[r.relevance].color}
            style={{ cursor: "pointer" }}
            onClick={() => onPick(r.rank)}
          >
            <title>{`rank ${r.rank} (prime ${r.prime_rank}) · relevance ${r.relevance}`}</title>
          </rect>
        ))}
      </svg>
      <div className="d-flex justify-content-between small text-muted">
        <span>1</span>
        <span>{topK}</span>
      </div>
    </div>
  );
}

function ResultCard({ r, highlight, textOnly }) {
  const m = modality(r);
  return (
    <div id={`rank-${r.rank}`} className={`card mb-2 ${highlight ? "border-primary border-2" : ""}`}>
      <div className="card-header d-flex flex-wrap gap-2 align-items-center small py-1">
        <strong className="font-monospace">#{r.rank}</strong>
        <span className="text-muted font-monospace" title="rank after removing unjudged answers (used by the metrics)">
          ′{r.prime_rank ?? "–"}
        </span>
        <RelevanceBadge relevance={r.relevance} />
        {!textOnly && (
          <span className={`badge ${m.cls}`} title="which modality retrieved this answer">
            {m.label}
          </span>
        )}
        <span className="text-muted">
          answer {r.post_id}
        </span>
        {r.silver_post_id != null && <span className="text-muted">silver_id: {r.silver_post_id}</span>}
        <span className="ms-auto text-muted font-monospace">
          {textOnly ? (
            <>colbert {fmt(r.score, 2)}</>
          ) : (
            <>
              rrf {r.score.toFixed(4)} · formula {fmt(r.formula_score)} · text {fmt(r.text_score, 2)}
            </>
          )}
        </span>
      </div>
      <div className="card-body py-2">
        {r.question && (
          <div className="small mb-1">
            <span className="text-muted">Q: </span>
            <span className="link-body-emphasis">
              <MathText text={r.question.title ?? `question ${r.question.post_id}`} />
            </span>
          </div>
        )}
        <CollapsibleMath text={r.text} />
      </div>
    </div>
  );
}

function MissedRelevant({ missed }) {
  const [open, setOpen] = useState(false);
  const notIndexed = missed.filter((m) => !m.indexed);
  const indexed = missed.filter((m) => m.indexed);
  if (missed.length === 0) return <div className="alert alert-success py-2">Every relevant (≥ 2) answer was retrieved.</div>;
  return (
    <div className="card mb-4 border-warning">
      {/* <div className="card-header d-flex align-items-center gap-2" role="button" onClick={() => setOpen((v) => !v)}>
        <span>{open ? "▾" : "▸"}</span>
        <strong>Missed relevant answers: {missed.length}</strong>
        <span className="small text-muted">
          {indexed.length} indexed but not retrieved (retriever misses) · {notIndexed.length} not in the index (coverage)
        </span>
      </div> */}
      {open && (
        <div className="card-body">
          {[
            ["Indexed but not retrieved", indexed],
            ["Not in the index", notIndexed],
          ].map(
            ([title, list]) =>
              list.length > 0 && (
                <div key={title} className="mb-3">
                  <h6>
                    {title} ({list.length})
                  </h6>
                  {list.map((m) => (
                    <div key={m.post_id} className={`border rounded p-2 mb-2 ${m.indexed ? "" : "bg-body-tertiary"}`}>
                      <div className="d-flex flex-wrap gap-2 align-items-center small mb-1">
                        <RelevanceBadge relevance={m.relevance} />
                        {!m.indexed && <span className="badge text-bg-secondary">not indexed</span>}
                        <span className="text-muted">
                          answer {m.post_id}
                        </span>
                        {m.question && (
                          <span className="link-body-emphasis">
                            Q: <MathText text={m.question.title ?? `question ${m.question.post_id}`} />
                          </span>
                        )}
                      </div>
                      <CollapsibleMath text={m.text} previewChars={300} collapsedHeight="4.5em" />
                    </div>
                  ))}
                </div>
              )
          )}
        </div>
      )}
    </div>
  );
}

export default function Task1TopicView() {
  const { topicId } = useParams();
  const [settings, update] = useTask1Settings();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [startedAt, setStartedAt] = useState(null);
  const [judgedOnly, setJudgedOnly] = useState(false);
  const [modalityFilter, setModalityFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [highlight, setHighlight] = useState(null);
  const loading = !data && !error;
  const elapsed = useElapsed(startedAt, loading ? null : startedAt);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    setStartedAt(Date.now());
    setPage(0);
    loadTopicResults(topicId, settings)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicId, settings.arqmathVersion, settings.retriever, settings.topK]);

  const filtered = useMemo(() => {
    if (!data) return [];
    // The modality filter is hidden for the text retriever (everything is "text"): ignore it there.
    const byModality = modalityFilter !== "all" && data.retriever !== "text";
    return data.results.filter(
      (r) => (!judgedOnly || r.relevance != null) && (!byModality || modality(r).key === modalityFilter)
    );
  }, [data, judgedOnly, modalityFilter]);

  const nPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageRows = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const modalityCounts = useMemo(() => {
    const c = { formula: 0, text: 0, both: 0 };
    for (const r of data?.results ?? []) c[modality(r).key] = (c[modality(r).key] ?? 0) + 1;
    return c;
  }, [data]);

  // Jump to a rank from the strip: reset filters so the rank is on a page, then scroll to it.
  const pickRank = (rank) => {
    const inFiltered = filtered.findIndex((r) => r.rank === rank);
    let idx = inFiltered;
    if (idx < 0) {
      setJudgedOnly(false);
      setModalityFilter("all");
      idx = data.results.findIndex((r) => r.rank === rank);
    }
    setPage(Math.floor(idx / pageSize));
    setHighlight(rank);
  };
  useEffect(() => {
    if (highlight != null) document.getElementById(`rank-${highlight}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlight, page]);

  const m = data?.metrics;
  const textOnly = (data?.retriever ?? settings.retriever) === "text";
  const backLink = `/task1?${settingsToParams(settings)}`;

  return (
    <div className="container py-4">
      <div className="d-flex flex-wrap align-items-center gap-3 mb-3">
        <Link to={backLink}>← All topics</Link>
        <span className="small text-muted ms-auto">
          ARQMath-{settings.arqmathVersion} · {retrieverLabel(settings.retriever)} · top_k {settings.topK}
        </span>
        <RetrieverPicker value={settings.retriever} onChange={(retriever) => update({ retriever })} />
      </div>

      <h1 className="h3">Topic {topicId}</h1>

      {loading && (
        <div className="alert alert-info d-flex align-items-center gap-3">
          <div className="spinner-border spinner-border-sm" role="status" />
          Retrieving answers for {topicId}… <span className="font-monospace">{formatDuration(elapsed)}</span>
          <span className="small text-muted">({retrieverInfo(settings.retriever).perTopic})</span>
        </div>
      )}
      {error && <div className="alert alert-danger">{error}</div>}

      {data && (
        <>
          <div className="card mb-3">
            <div className="card-body">
              <CollapsibleMath text={data.content} previewChars={800} collapsedHeight="10em" />
            </div>
          </div>

          <dl className="row small mb-3">
            <dt className="col-sm-2">Formula query</dt>
            <dd className="col-sm-10 d-flex flex-wrap gap-2">
              {data.formulas.length > 0 ? (
                data.formulas.map((f, i) => (
                  <span key={i} className="border rounded-pill px-2 py-1 bg-body-tertiary" title={f}>
                    <Formula latex={f} />
                  </span>
                ))
              ) : (
                <span className="text-muted fst-italic">
                  {textOnly ? "none(text only)" : "no formulas"}
                </span>
              )}
            </dd>
            <dt className="col-sm-2">Text query</dt>
            <dd className="col-sm-10 text-muted">{data.text_query || <span className="fst-italic">empty</span>}</dd>
          </dl>

          {m ? (
            <>
              <div className="row row-cols-2 row-cols-md-5 g-3 mb-3">
                <MetricCard label="nDCG′" value={m.metrics.ndcg_prime} />
                <MetricCard label="MAP′" value={m.metrics.map_prime} />
                <MetricCard label="P′@10" value={m.metrics.p_prime_at_10} />
                {/* <MetricCard
                  label="Retrieved judged"
                  value={`${m.n_retrieved_judged}/${m.n_retrieved}`}
                  hint={`of ${m.n_judged} judged answers`}
                /> */}
                {/* <MetricCard
                  label="Relevant retrieved"
                  value={`${m.n_relevant - data.missed_relevant.length}/${m.n_relevant}`}
                  hint="relevance ≥ 2"
                /> */}
              </div>
              {/* <CoverageWarning coverage={m.judged_coverage} arqmathVersion={data.arqmath_version} /> */}
            </>
          ) : (
            <div className="alert alert-secondary py-2">This topic has no judgments: results are shown without metrics.</div>
          )}

          {m && <MissedRelevant missed={data.missed_relevant} />}

          {m && <RankStrip results={data.results} topK={data.top_k} onPick={pickRank} />}

          <div className="d-flex flex-wrap align-items-center gap-3 mb-2">
            <div className="form-check form-switch mb-0">
              <input
                id="t1-judged-only"
                className="form-check-input"
                type="checkbox"
                checked={judgedOnly}
                onChange={(e) => {
                  setJudgedOnly(e.target.checked);
                  setPage(0);
                }}
              />
              <label className="form-check-label small" htmlFor="t1-judged-only">
                Judged only
              </label>
            </div>
{!textOnly && (
            <select
              className="form-select form-select-sm"
              style={{ width: "auto" }}
              value={modalityFilter}
              onChange={(e) => {
                setModalityFilter(e.target.value);
                setPage(0);
              }}
            >
              <option value="all">All modalities ({data.results.length})</option>
              <option value="both">Formula + text ({modalityCounts.both})</option>
              <option value="formula">Formula only ({modalityCounts.formula})</option>
              <option value="text">Text only ({modalityCounts.text})</option>
            </select>
            )}
            <span className="small text-muted">{filtered.length} results</span>
            <div className="ms-auto d-flex align-items-center gap-2">
              <select
                className="form-select form-select-sm"
                style={{ width: "auto" }}
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(0);
                }}
              >
                {PAGE_SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s} / page
                  </option>
                ))}
              </select>
              <Pager page={page} nPages={nPages} setPage={setPage} />
            </div>
          </div>

          {pageRows.map((r) => (
            <ResultCard key={r.rank} r={r} highlight={r.rank === highlight} textOnly={textOnly} />
          ))}
          {pageRows.length === 0 && <p className="text-muted fst-italic">No results.</p>}

          <div className="d-flex justify-content-end mt-2">
            <Pager page={page} nPages={nPages} setPage={setPage} />
          </div>
        </>
      )}
    </div>
  );
}

function Pager({ page, nPages, setPage }) {
  return (
    <div className="btn-group btn-group-sm align-items-center">
      <button type="button" className="btn btn-outline-secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
        ‹ Prev
      </button>
      <span className="btn btn-outline-secondary disabled text-body">
        {page + 1} / {nPages}
      </span>
      <button type="button" className="btn btn-outline-secondary" disabled={page >= nPages - 1} onClick={() => setPage(page + 1)}>
        Next ›
      </button>
    </div>
  );
}
