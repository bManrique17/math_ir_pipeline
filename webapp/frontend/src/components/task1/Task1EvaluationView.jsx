import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchTask1Topics } from "../../api";
import {
  CoverageWarning,
  MathText,
  MetricCard,
  clearEvaluation,
  fmt,
  formatDuration,
  RetrieverPicker,
  retrieverInfo,
  retrieverLabel,
  settingsToParams,
  startEvaluation,
  truncateMath,
  useElapsed,
  useEvaluationRun,
  useRetrieverRuns,
  useTask1Settings,
} from "./shared";

const topicNum = (id) => Number(id.split(".")[1]) || 0;

// Sortable columns: value getter from a merged {topic, q} row (q = per_query row or null).
const COLUMNS = [
  { key: "topic_id", label: "Topic", get: (r) => topicNum(r.topic.topic_id) },
  { key: "n_judged", label: "Judged", get: (r) => r.topic.n_judged, num: true },
  { key: "n_relevant", label: "Rel docs total", get: (r) => r.topic.n_relevant, num: true },
  { key: "ndcg_prime", label: "nDCG′", get: (r) => r.q?.metrics.ndcg_prime, num: true, metric: true },
  { key: "map_prime", label: "MAP′", get: (r) => r.q?.metrics.map_prime, num: true, metric: true },
  { key: "p_prime_at_10", label: "P′@10", get: (r) => r.q?.metrics.p_prime_at_10, num: true, metric: true },
  { key: "n_retrieved_judged", label: "Qrels labeled", get: (r) => r.q?.n_retrieved_judged, num: true },
];

function SettingsForm({ settings, update, disabled }) {
  return (
    <div className="d-flex flex-wrap align-items-end gap-3 mb-3">
      {/* <div>
        <label className="form-label small text-muted mb-1" htmlFor="t1-version">
          ARQMath edition
        </label>
        <select
          id="t1-version"
          className="form-select form-select-sm"
          value={settings.arqmathVersion}
          disabled={disabled}
          onChange={(e) => update({ arqmathVersion: Number(e.target.value) })}
        >
          <option value={1}>ARQMath-1</option>
          <option value={2}>ARQMath-2 (low coverage)</option>
          <option value={3}>ARQMath-3 (low coverage)</option>
        </select>
      </div> */}
      <div>
        <div className="form-label small text-muted mb-1">Retriever</div>
        <RetrieverPicker value={settings.retriever} disabled={disabled} onChange={(retriever) => update({ retriever })} />
      </div>
      <div>
        <label className="form-label small text-muted mb-1" htmlFor="t1-topk">
          top k
        </label>
        <input
          id="t1-topk"
          type="number"
          min={1}
          max={1000}
          className="form-control form-control-sm"
          style={{ width: "100px" }}
          value={settings.topK}
          disabled={disabled}
          onChange={(e) => {
            const k = Number(e.target.value);
            if (Number.isInteger(k) && k >= 1 && k <= 1000) update({ topK: k });
          }}
        />
      </div>
      {settings.topK !== 1000 && <div className="small text-warning-emphasis">top k ≠ 1000: metrics not ARQMath-comparable</div>}
    </div>
  );
}

function MetricBar({ value }) {
  if (value == null) return <span className="text-muted">–</span>;
  return (
    <div className="d-flex align-items-center gap-2">
      <span className="font-monospace" style={{ width: "3.2em" }}>
        {fmt(value)}
      </span>
      <div className="flex-grow-1 bg-body-secondary rounded" style={{ height: 6, minWidth: 40 }}>
        <div className="bg-primary rounded" style={{ height: 6, width: `${Math.min(1, value) * 100}%` }} />
      </div>
    </div>
  );
}

export default function Task1EvaluationView() {
  const navigate = useNavigate();
  const [settings, update] = useTask1Settings();
  const [run, anyRunning] = useEvaluationRun(settings);
  const running = run?.status === "running";
  const elapsed = useElapsed(run?.startedAt, run?.finishedAt);

  const [topics, setTopics] = useState(null);
  const [topicsError, setTopicsError] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [evaluatedOnly, setEvaluatedOnly] = useState(true);
  const [sort, setSort] = useState({ key: "topic_id", dir: 1 });

  useEffect(() => {
    let cancelled = false;
    setTopics(null);
    setTopicsError(null);
    setSelected(new Set());
    fetchTask1Topics(settings.arqmathVersion)
      .then((d) => !cancelled && setTopics(d.topics))
      .catch((e) => !cancelled && setTopicsError(e.message));
    return () => {
      cancelled = true;
    };
  }, [settings.arqmathVersion]);

  const evalData = run?.data ?? null;
  const perQuery = useMemo(() => new Map((evalData?.per_query ?? []).map((q) => [q.topic_id, q])), [evalData]);
  const failed = useMemo(() => new Set(evalData?.failed_topics ?? []), [evalData]);

  // Other retrievers with a finished run for the same edition / top_k: one extra column each,
  // sorted by the nDCG′ difference (current − other).
  const retrieverRuns = useRetrieverRuns(settings);
  const compareCols = useMemo(
    () =>
      retrieverRuns
        .filter((x) => x.retriever !== settings.retriever)
        .map(({ retriever, run: other }) => {
          const byTopic = new Map(other.data.per_query.map((q) => [q.topic_id, q.metrics.ndcg_prime]));
          return {
            key: `cmp:${retriever}`,
            label: `vs ${retrieverInfo(retriever).short}`,
            title: `nDCG′ of ${retrieverLabel(retriever)}; Δ = current − it`,
            num: true,
            metric: true,
            other: (r) => byTopic.get(r.topic.topic_id),
            get: (r) => {
              const o = byTopic.get(r.topic.topic_id);
              const c = r.q?.metrics.ndcg_prime;
              return o == null || c == null ? null : c - o;
            },
          };
        }),
    [retrieverRuns, settings.retriever]
  );
  // const allColumns = [...COLUMNS, ...compareCols];
  const allColumns = [...COLUMNS];

  const rows = useMemo(() => {
    if (!topics) return [];
    const col = allColumns.find((c) => c.key === sort.key) ?? COLUMNS[0];
    return topics
      .filter((t) => !evaluatedOnly || t.evaluated)
      .map((t) => ({ topic: t, q: perQuery.get(t.topic_id) ?? null }))
      .sort((a, b) => {
        const va = col.get(a);
        const vb = col.get(b);
        if (va == null && vb == null) return topicNum(a.topic.topic_id) - topicNum(b.topic.topic_id);
        if (va == null) return 1; // missing values always last
        if (vb == null) return -1;
        return (va - vb) * sort.dir || topicNum(a.topic.topic_id) - topicNum(b.topic.topic_id);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topics, perQuery, evaluatedOnly, sort, compareCols]);

  const nEvaluated = topics?.filter((t) => t.evaluated).length ?? 0;
  const selectableIds = rows.filter((r) => r.topic.evaluated).map((r) => r.topic.topic_id);
  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selected.has(id));

  const toggle = (id) =>
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });

  const onSort = (key) =>
    setSort((s) => (s.key === key ? { key, dir: -s.dir } : { key, dir: allColumns.find((c) => c.key === key)?.metric ? -1 : 1 }));

  const evaluateSelected = () => {
    const ids = [...selected].sort((a, b) => topicNum(a) - topicNum(b));
    startEvaluation(settings, ids);
  };
  const evaluateAll = () => {
    if (window.confirm(`Evaluate all ${nEvaluated} judged topics?`)) {
      startEvaluation(settings, null);
    }
  };

  const openTopic = (id) => navigate(`/task1/topics/${encodeURIComponent(id)}?${settingsToParams(settings)}`);

  return (
    <div className="container py-4">

      <SettingsForm settings={settings} update={update} disabled={running} />

      <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
        <button type="button" className="btn btn-primary" disabled={anyRunning || selected.size === 0} onClick={evaluateSelected}>
          Evaluate selected ({selected.size})
        </button>
        <button type="button" className="btn btn-outline-primary" disabled={anyRunning || nEvaluated === 0} onClick={evaluateAll}>
          Evaluate all ({nEvaluated})
        </button>
        {run && !running && (
          <button type="button" className="btn btn-link btn-sm text-muted" onClick={() => clearEvaluation(settings)}>
            Clear result
          </button>
        )}
        {anyRunning && !running && <span className="small text-muted">An evaluation with other settings is running.</span>}
      </div>

      {running && (
        <div className="alert alert-info d-flex align-items-center gap-3">
          <div className="spinner-border spinner-border-sm" role="status" />
          <div>
            Evaluating {run.topicIds ? `${run.topicIds.length} topic${run.topicIds.length === 1 ? "" : "s"}` : "all topics"} with the{" "}
            {retrieverLabel(settings.retriever)} retriever… <span className="font-monospace">{formatDuration(elapsed)}</span>

          </div>
        </div>
      )}
      {run?.status === "error" && <div className="alert alert-danger">Evaluation failed: {run.error}</div>}

      {evalData && (
        <section className="mb-4">
          {/* <div className="d-flex flex-wrap gap-3 align-items-baseline mb-2 small text-muted">
            <span>
              retriever <code>{evalData.retriever}</code>
            </span>
            <span>top_k {evalData.top_k}</span>
            <span>
              {evalData.n_topics} topic{evalData.n_topics === 1 ? "" : "s"}
              {run.topicIds ? " (selection)" : " (all judged)"}
            </span>
            {run.finishedAt && (
              <span>
                finished {new Date(run.finishedAt).toLocaleString()} in {formatDuration(Math.round((run.finishedAt - run.startedAt) / 1000))}
              </span>
            )}
          </div>
          <div className="row row-cols-2 row-cols-md-4 g-3 mb-3">
            <MetricCard label="nDCG′" value={evalData.aggregate.ndcg_prime} />
            <MetricCard label="MAP′" value={evalData.aggregate.map_prime} />
            <MetricCard label="P′@10" value={evalData.aggregate.p_prime_at_10} />
            <MetricCard label="Judged coverage" value={`${(evalData.judged_coverage * 100).toFixed(1)}%`} />
          </div>
          <CoverageWarning coverage={evalData.judged_coverage} arqmathVersion={evalData.arqmath_version} />
          {evalData.failed_topics.length > 0 && (
            <div className="alert alert-danger py-2">
              Retrieval failed for {evalData.failed_topics.length} topic(s), scored 0: {evalData.failed_topics.join(", ")}
            </div>
          )} */}
        </section>
      )}

      {retrieverRuns.length >= 2 && <RetrieverComparison retrieverRuns={retrieverRuns} current={settings.retriever} />}

      {topicsError && <div className="alert alert-danger">Failed to load topics: {topicsError}</div>}
      {!topics && !topicsError && <p className="text-muted">Loading topics…</p>}

      {topics && (
        <>
          <div className="d-flex align-items-center gap-3 mb-2">
            {/* <span className="text-muted small">
              {topics.length} topics, {nEvaluated} with judgments
            </span> */}
            {/* <div className="form-check form-switch mb-0 ms-auto">
              <input
                id="t1-evaluated-only"
                className="form-check-input"
                type="checkbox"
                checked={evaluatedOnly}
                onChange={(e) => setEvaluatedOnly(e.target.checked)}
              />
              <label className="form-check-label small" htmlFor="t1-evaluated-only">
                Judged topics only
              </label>
            </div> */}
          </div>
          <div className="table-responsive">
            <table className="table table-sm table-hover align-middle">
              <thead>
                <tr>
                  <th style={{ width: 30 }}>
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={allSelected}
                      disabled={selectableIds.length === 0}
                      title="Select all judged topics shown"
                      onChange={() => setSelected(allSelected ? new Set() : new Set(selectableIds))}
                    />
                  </th>
                  <SortHeader col={COLUMNS[0]} sort={sort} onSort={onSort} />
                  <th>Question</th>
                  {allColumns.slice(1).map((c) => (
                    <SortHeader key={c.key} col={c} sort={sort} onSort={onSort} />
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map(({ topic: t, q }) => (
                  <tr
                    key={t.topic_id}
                    role="button"
                    className={t.evaluated ? "" : "text-muted"}
                    onClick={() => openTopic(t.topic_id)}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        disabled={!t.evaluated}
                        title={t.evaluated ? undefined : "No judgments: not part of the evaluation"}
                        checked={selected.has(t.topic_id)}
                        onChange={() => toggle(t.topic_id)}
                      />
                    </td>
                    <td className="text-nowrap fw-semibold">
                      {t.topic_id}
                      {failed.has(t.topic_id) && <span className="badge text-bg-danger ms-1">failed</span>}
                    </td>
                    <td className="small" style={{ maxWidth: 420 }}>
                      <MathText text={truncateMath(t.content, 140)} />
                    </td>
                    <td className="text-end font-monospace">{t.n_judged}</td>
                    <td className="text-end font-monospace">{t.n_relevant}</td>
                    {/* <td style={{ minWidth: 120 }}>
                      <MetricBar value={q?.metrics.ndcg_prime} />
                    </td> */}
                    
                    <td className="font-monospace">{fmt(q?.metrics.ndcg_prime)}</td>
                    <td className="font-monospace">{fmt(q?.metrics.map_prime)}</td>
                    <td className="font-monospace">{fmt(q?.metrics.p_prime_at_10)}</td>
                    <td className="text-end font-monospace">
                      {q ? (
                        <span title={`${q.n_retrieved_judged} judged of ${q.n_retrieved} retrieved`}>
                          {q.n_retrieved_judged}/{q.n_retrieved}
                        </span>
                      ) : (
                        "–"
                      )}
                      {q && q.judged_coverage < 0.95 && (
                        <span className="text-warning-emphasis ms-1" title={`judged coverage ${(q.judged_coverage * 100).toFixed(0)}%`}>
                          ⚠
                        </span>
                      )}
                    </td>
                    {/* {compareCols.map((c) => (
                      <td key={c.key} className="font-monospace text-nowrap">
                        <CompareCell other={c.other({ topic: t })} delta={c.get({ topic: t, q })} />
                      </td>
                    ))} */}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function SortHeader({ col, sort, onSort }) {
  const active = sort.key === col.key;
  return (
    <th
      role="button"
      title={col.title}
      className={`text-nowrap user-select-none ${col.num && !col.metric ? "text-end" : ""}`}
      onClick={() => onSort(col.key)}
    >
      {col.label}
      <span className={active ? "" : "text-body-tertiary"}> {active ? (sort.dir > 0 ? "▲" : "▼") : "↕"}</span>
    </th>
  );
}

// Other retriever's nDCG′ for a topic and the current retriever's difference to it.
function CompareCell({ other, delta }) {
  if (other == null) return <span className="text-muted">–</span>;
  return (
    <>
      {fmt(other)}
      {delta != null && (
        <span className={`ms-1 small ${delta > 0.0005 ? "text-success" : delta < -0.0005 ? "text-danger" : "text-muted"}`}>
          {delta > 0 ? "+" : ""}
          {delta.toFixed(3)}
        </span>
      )}
    </>
  );
}

// Aggregates of every retriever with a finished run, recomputed over the topics all runs share
// (runs may cover different topic selections), plus per-topic wins/losses vs the current retriever.
function RetrieverComparison({ retrieverRuns, current }) {
  const common = retrieverRuns
    .map((x) => new Set(x.run.data.per_query.map((q) => q.topic_id)))
    .reduce((acc, s) => new Set([...acc].filter((id) => s.has(id))));
  const metricsOf = (x) => new Map(x.run.data.per_query.map((q) => [q.topic_id, q.metrics]));
  const mean = (m, key) => (common.size ? [...common].reduce((s, id) => s + m.get(id)[key], 0) / common.size : null);
  const cur = retrieverRuns.find((x) => x.retriever === current);
  const curMetrics = cur ? metricsOf(cur) : null;

  const rows = retrieverRuns.map((x) => {
    const m = metricsOf(x);
    let wins = 0;
    let losses = 0;
    if (curMetrics && x.retriever !== current) {
      for (const id of common) {
        const d = curMetrics.get(id).ndcg_prime - m.get(id).ndcg_prime;
        if (d > 0.0005) wins += 1;
        else if (d < -0.0005) losses += 1;
      }
    }
    return {
      retriever: x.retriever,
      ndcg: mean(m, "ndcg_prime"),
      map: mean(m, "map_prime"),
      p10: mean(m, "p_prime_at_10"),
      wins,
      losses,
    };
  });
  const best = Math.max(...rows.map((r) => r.ndcg ?? -1));

  return (
    <section className="mb-4">
      {/* <h2 className="h6 mb-1">Retriever comparison</h2> */}
      {/* <p className="small text-muted mb-2">
        Means over the {common.size} topic{common.size === 1 ? "" : "s"} evaluated by every retriever below
        {common.size === 0 && " — run them on the same topics to compare"}. Per-topic nDCG′ of the other retrievers
        is added to the table (Δ = current − other).
      </p> */}
      <div className="table-responsive">
        <table className="table table-sm align-middle mb-0" style={{ maxWidth: 760 }}>
          <thead>
            <tr>
              <th>Retriever</th>
              <th>nDCG′</th>
              <th>MAP′</th>
              <th>P′@10</th>
              {/* {cur && <th title="topics where the current retriever has higher / lower nDCG′">current better / worse</th>} */}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.retriever} className={r.retriever === current ? "table-primary" : ""}>
                <td>
                  {retrieverInfo(r.retriever).label}
                  {r.retriever === current && <span className="badge text-bg-primary ms-2">current</span>}
                </td>
                <td className={`font-monospace ${r.ndcg === best && rows.length > 1 ? "fw-bold" : ""}`}>{fmt(r.ndcg)}</td>
                <td className="font-monospace">{fmt(r.map)}</td>
                <td className="font-monospace">{fmt(r.p10)}</td>
                {/* {cur && (
                  <td>
                    {r.retriever === current ? (
                      ""
                    ) : (
                      <>
                        <span className="text-success">{r.wins}</span> / <span className="text-danger">{r.losses}</span>
                      </>
                    )}
                  </td>
                )} */}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
