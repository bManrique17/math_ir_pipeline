// Shared pieces of the ARQMath Task 1 views: settings in the URL, client-side caches
// (topic results, evaluation runs), and small rendering helpers.
import { useEffect, useState, useSyncExternalStore } from "react";
import { useSearchParams } from "react-router-dom";

import { fetchTask1Evaluation, fetchTask1TopicResults } from "../../api";
import { useMathJaxTypeset } from "../../hooks/useMathJax";

// ---------------------------------------------------------------- settings

// Retrievers of the /task1 API. Timings are the API docs' estimates (all ARQMath-1 topics / one topic).
export const RETRIEVERS = [
  { id: "text", short: "Text", label: "text only (ColBERT baseline)", minutesAll: 3, perTopic: "~2–3 s" },
  { id: "formula_isolated_plus_text", short: "Isolated + text", label: "isolated formulas + text", minutesAll: 25, perTopic: "~5–80 s" },
  { id: "formula_annotated_plus_text", short: "Annotated + text", label: "annotated formulas + text", minutesAll: 35, perTopic: "~5–80 s" },
];
const RETRIEVER_BY_ID = Object.fromEntries(RETRIEVERS.map((r) => [r.id, r]));
export const retrieverInfo = (id) => RETRIEVER_BY_ID[id] ?? { id, short: id, label: id, minutesAll: null, perTopic: null };
export const retrieverLabel = (id) => retrieverInfo(id).label;

export const DEFAULT_SETTINGS = { arqmathVersion: 1, retriever: "formula_isolated_plus_text", topK: 1000 };

// Settings live in the query string so a topic link / reload keeps them.
export function useTask1Settings() {
  const [params, setParams] = useSearchParams();
  const v = Number(params.get("v"));
  const k = Number(params.get("top_k"));
  const retriever = params.get("retriever");
  const settings = {
    arqmathVersion: [1, 2, 3].includes(v) ? v : DEFAULT_SETTINGS.arqmathVersion,
    retriever: RETRIEVER_BY_ID[retriever] ? retriever : DEFAULT_SETTINGS.retriever,
    topK: Number.isInteger(k) && k >= 1 && k <= 1000 ? k : DEFAULT_SETTINGS.topK,
  };
  const update = (patch) => {
    const next = { ...settings, ...patch };
    setParams(settingsToParams(next), { replace: true });
  };
  return [settings, update];
}

export function settingsToParams({ arqmathVersion, retriever, topK }) {
  return new URLSearchParams({ v: arqmathVersion, retriever, top_k: topK });
}

export const settingsKey = ({ arqmathVersion, retriever, topK }) => `v${arqmathVersion}|r:${retriever}|k${topK}`;

export function RetrieverPicker({ value, onChange, disabled }) {
  return (
    <div className="btn-group btn-group-sm" role="group" aria-label="Retriever">
      {RETRIEVERS.map((r) => (
        <button
          key={r.id}
          type="button"
          disabled={disabled}
          title={r.label}
          className={`btn ${value === r.id ? "btn-primary" : "btn-outline-primary"}`}
          onClick={() => onChange(r.id)}
        >
          {r.short}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- topic results cache

// Full (unpaged, judged_only=false) response per (topic, settings); filtering and paging
// are done client-side. Stores the promise so concurrent mounts share one request.
const topicResultsCache = new Map();

export function loadTopicResults(topicId, settings) {
  const key = `${topicId}|${settingsKey(settings)}`;
  if (!topicResultsCache.has(key)) {
    const p = fetchTask1TopicResults(topicId, { ...settings, limit: 1000 });
    p.catch(() => topicResultsCache.delete(key)); // don't cache failures
    topicResultsCache.set(key, p);
  }
  return topicResultsCache.get(key);
}

// ---------------------------------------------------------------- evaluation runs store

// One run per settings key (the latest one). Kept at module level so a run survives
// navigating to a topic and back; finished runs are also persisted in localStorage
// (an evaluation of all topics takes ~30 min).
const STORAGE_PREFIX = "task1-eval:";
const runs = new Map(); // key -> {status: "running"|"done"|"error", data, error, topicIds, startedAt, finishedAt}
const listeners = new Set();
let version = 0;

function emit() {
  version += 1;
  listeners.forEach((l) => l());
}

function readStored(key) {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function getRun(key) {
  if (!runs.has(key)) {
    const stored = readStored(key);
    if (stored) runs.set(key, stored);
  }
  return runs.get(key) ?? null;
}

export function isAnyRunRunning() {
  for (const r of runs.values()) if (r.status === "running") return true;
  return false;
}

export function startEvaluation(settings, topicIds) {
  const key = settingsKey(settings);
  const run = { status: "running", data: null, error: null, topicIds, startedAt: Date.now(), finishedAt: null };
  runs.set(key, run);
  emit();
  fetchTask1Evaluation({ ...settings, topicIds })
    .then((data) => {
      const done = { ...run, status: "done", data, finishedAt: Date.now() };
      runs.set(key, done);
      try {
        localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(done));
      } catch {
        /* storage full / unavailable: keep in memory only */
      }
    })
    .catch((e) => {
      // Keep the previous stored result visible below the error.
      runs.set(key, { ...run, status: "error", error: e.message, data: readStored(key)?.data ?? null, finishedAt: Date.now() });
    })
    .finally(emit);
}

export function clearEvaluation(settings) {
  const key = settingsKey(settings);
  runs.delete(key);
  try {
    localStorage.removeItem(STORAGE_PREFIX + key);
  } catch {
    /* ignore */
  }
  emit();
}

const subscribe = (l) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

// Returns [run for these settings, any run in progress].
export function useEvaluationRun(settings) {
  useSyncExternalStore(subscribe, () => version);
  return [getRun(settingsKey(settings)), isAnyRunRunning()];
}

// Finished runs of every retriever for the same edition / top_k (for side-by-side comparison):
// [{retriever, run}] in RETRIEVERS order, only those with results.
export function useRetrieverRuns(settings) {
  useSyncExternalStore(subscribe, () => version);
  return RETRIEVERS.map((r) => ({ retriever: r.id, run: getRun(settingsKey({ ...settings, retriever: r.id })) })).filter(
    (x) => x.run?.data
  );
}

// Per-topic metrics row from the latest evaluation run for these settings, if any.
export function useStoredTopicMetrics(settings, topicId) {
  const [run] = useEvaluationRun(settings);
  return run?.data?.per_query?.find((q) => q.topic_id === topicId) ?? null;
}

// ---------------------------------------------------------------- rendering helpers

// Text with inline `$...$` (and `$$...$$`) LaTeX -> MathJax delimiters. Unbalanced `$` are left as-is.
function toMathJax(text) {
  return text.replace(/\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g, (_, display, inline) =>
    display != null ? `\\[${display}\\]` : `\\(${inline}\\)`
  );
}

// Cut text to ~n chars without leaving an unclosed `$`.
export function truncateMath(text, n) {
  if (!text || text.length <= n) return text ?? "";
  let cut = text.slice(0, n);
  if ((cut.match(/\$/g) ?? []).length % 2 === 1) cut = cut.slice(0, cut.lastIndexOf("$"));
  return `${cut.trimEnd()} …`;
}

// Plain text with `$...$` math, typeset by MathJax. Keyed by content so React remounts
// instead of diffing DOM that MathJax already replaced.
export function MathText({ text, as: Tag = "span", className, style }) {
  return <MathTextInner key={text} text={text} Tag={Tag} className={className} style={style} />;
}

function MathTextInner({ text, Tag, className, style }) {
  const ref = useMathJaxTypeset([text]);
  return (
    <Tag ref={ref} className={className} style={style}>
      {toMathJax(text ?? "")}
    </Tag>
  );
}

export function Formula({ latex }) {
  return <MathText text={`$${latex}$`} />;
}

// Long text collapsed to a few lines with a toggle.
export function CollapsibleMath({ text, previewChars = 400, collapsedHeight = "6.5em" }) {
  const [expanded, setExpanded] = useState(false);
  if (!text) return <span className="text-muted fst-italic">(no text)</span>;
  const collapsible = text.length > previewChars;
  return (
    <>
      <div style={collapsible && !expanded ? { maxHeight: collapsedHeight, overflow: "hidden" } : undefined}>
        <MathText text={text} as="div" style={{ whiteSpace: "pre-wrap" }} />
      </div>
      {collapsible && (
        <button type="button" className="btn btn-link btn-sm p-0 mt-1" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </>
  );
}

export const RELEVANCE = {
  3: { label: "high", color: "#198754", cls: "text-bg-success" },
  2: { label: "medium", color: "#0d6efd", cls: "text-bg-primary" },
  1: { label: "low", color: "#e0a800", cls: "text-bg-warning" },
  0: { label: "not relevant", color: "#dc3545", cls: "text-bg-danger" },
};

export function RelevanceBadge({ relevance }) {
  if (relevance == null) return <span className="badge bg-secondary-subtle text-secondary-emphasis">not judged</span>;
  const r = RELEVANCE[relevance];
  return (
    <span className={`badge ${r.cls}`} title={`relevance ${relevance}`}>
      {relevance} · {r.label}
    </span>
  );
}

export const fmt = (x, digits = 3) => (x == null ? "–" : x.toFixed(digits));

export function MetricCard({ label, value, hint, digits = 3 }) {
  return (
    <div className="col">
      <div className="card h-100">
        <div className="card-body py-2">
          <div className="small text-muted">{label}</div>
          <div className="fs-4 fw-semibold font-monospace">{typeof value === "number" ? fmt(value, digits) : value}</div>
          {hint && <div className="small text-muted">{hint}</div>}
        </div>
      </div>
    </div>
  );
}

export function CoverageWarning({ coverage, arqmathVersion }) {
  if (coverage == null || coverage >= 0.95) return null;
  return (
    <div className="alert alert-warning py-2">
      {/* Judged coverage is {(coverage * 100).toFixed(1)}%: only that fraction of the judged answers exist in the index,
      so these scores are not comparable to official ARQMath results
      {arqmathVersion !== 1 && " (the index was built for ARQMath-1)"}. */}
    </div>
  );
}

// Seconds from `start` to `end` (or to now, ticking every second, while `end` is unset).
export function useElapsed(start, end) {
  const active = start != null && end == null;
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!active) return undefined;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [active]);
  return start != null ? Math.max(0, Math.floor(((end ?? now) - start) / 1000)) : 0;
}

export const formatDuration = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

