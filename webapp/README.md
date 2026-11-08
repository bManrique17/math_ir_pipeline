# Formula Descriptors Viewer

Eight tabs (top nav):

- **Posts** (`/`) — `{schema}.post_arqmath` rows: the post text (formulas
  rendered via MathJax) and, in one merged table, every formula referenced in
  that post alongside its extracted `formula_descriptors` sentences (one row
  per formula id, "Descriptions" column shows the sentences or "none"). Search
  by `silver_id` to jump to a single post.
- **Formulas** (`/formulas`) — all of `{schema}.formula_arqmath`, paginated.
  Two independent search bars: search by formula id, or filter to the formulas
  referenced by a given post id (reuses the Posts-tab post lookup under the
  hood).
- **Vocab** (`/vocab`) — search a `public.vocab` row by id (built by
  `ETL/main_create_vocab.py` / `make create-vocab`): its dataset and comments,
  plus SLT/OPT node and edge vocabs as id -> token -> count tables.
- **Formula retrieval** (`/retrieval`) — LaTeX query + top k, sent to the
  external retrieval service (`RETRIEVAL_URL`); shows the ranked
  `gold.formula` ids with their score and rendered LaTeX; "View graph" opens
  `/gold_formula/:id` (same graph page, raw gold OPT/SLT trees).
- **Multimodal retrieval** (`/multimodal_retrieval`) — free-text query with
  `$latex$` formulas, sent to the retrieval service's
  `retrieve_multimodal_posts`; shows how the query was split (formulas / text)
  and the ranked posts with their combined, formula and text scores. Post
  text is rendered like the Posts tab, from `silver.post_arqmath` /
  `silver.formula_arqmath` (always `silver`, independent of `PG_SCHEMA`, since
  those are the ids the service returns).
- **Annotated formula retrieval** (`/annotated_retrieval`) — free-text query
  with `$latex$` formulas (no `$` = the whole query is one formula), sent to
  the retrieval service's `retrieve_annotated_formula`, which has an LLM
  extract a description of each formula from the surrounding text and searches
  with formula + descriptors together. Shows how the query was understood
  (per formula: extracted descriptors, and the annotations actually used for
  the search) and the ranked formula occurrences with their score, LaTeX,
  annotations and source post; "View graph" opens `/silver_formula/:silver_id`
  (same graph page, annotated OPT when available).
- **Annotated multimodal retrieval** (`/multimodal_retrieval_annotated`) —
  same view as Multimodal retrieval, backed by
  `retrieve_multimodal_posts_annotated`.
- **ARQMath Task 1** (`/task1`) — evaluation of the multimodal post
  retriever on ARQMath Task 1 (answer retrieval), via the retrieval service's
  `/task1/*` API. Settings (edition 1–3, retriever: `text` ColBERT baseline /
  isolated formulas + text / annotated formulas + text, top k) live in the URL. The landing page lists the topics (sortable; judged
  topics only by default) and runs `/task1/evaluate` on the selected topics or
  all of them (blocking: ~3 min for all with `text`, ~25–35 min with the
  formula retrievers): aggregate nDCG′ / MAP′ / P′@10
  cards, judged-coverage warning, failed topics, and per-topic metrics merged
  into the table. The latest run per settings survives navigation and is kept
  in `localStorage`. When several retrievers have a finished run (same edition / top k), a
  comparison table shows their means over the topics they share and per-topic
  wins/losses, and the topic table gets one nDCG′ column per other retriever
  with Δ = current − other (sortable). Clicking a topic opens `/task1/topics/:topicId`: the topic
  (rendered), how it was split into formula/text queries, its metrics, the
  relevant answers that were missed (indexed vs. not in the index), a strip
  showing where the judged answers fall over ranks 1..top k, and the ranked
  answers (rank / prime rank, relevance badge, which modality found it, RRF /
  formula / text scores, parent question) with judged-only / modality filters
  and local paging. The full response is fetched once per (topic, settings)
  and cached in memory.

Both annotated tabs need the retrieval service to be started with the
annotated model; otherwise it answers `503` and the tab shows that message.
Queries with text and formulas take a few seconds (LLM call).

Every formula row, in either tab, links to `/formula/:id` — its OPT (operator
tree) and SLT (symbol layout tree) graphs from the gold layer, rendered
server-side as SVG (via `graphviz`) and pannable/zoomable in the browser (via
`svg-pan-zoom`: scroll to zoom, drag to pan, double-click to zoom in). Node
labels are the raw, unsplit tag (e.g. `V!x`); annotation nodes (attached
descriptor sentences) are styled distinctly from structural nodes, but
structural nodes are not colored by symbol type. OPT prefers the
post-context-annotated tree (`formula_arqmath.opt_nx_dict_annotated`, built by
`ETL/main_annotate_opt_formulas.py` / `make annotate-opt`) and falls back to
the raw gold tree when no annotation is available for that occurrence yet;
SLT is always the raw gold tree (there is no annotated SLT).

## Backend (FastAPI)

Requires the `dot` binary (Graphviz) on `PATH` for the formula graph view —
`sudo apt install graphviz` (or equivalent) if it's not already present; the
`graphviz` Python package (in `requirements.txt`) only wraps that CLI, it
doesn't ship it.

```bash
cd webapp/backend
bash setup_env.sh          # creates conda env "webapp_backend", installs requirements.txt
conda activate webapp_backend
uvicorn app.main:app --reload --port 8000
```

Configurable via env vars (defaults match `ETL/conf/config.yaml`):
- `PG_DSN` (default `postgresql://postgres:postgres@localhost:5432/math_ir`)
- `PG_SCHEMA` (default `debug_silver`) -- `post_arqmath` / `formula_arqmath`
- `PG_GOLD_SCHEMA` (default `debug_gold`) -- joined in for `opt_nx_dict`/`slt_nx_dict` on the formula graph view
- `RETRIEVAL_URL` (default `http://localhost:8008`) -- retrieval service behind `/api/retrieval` (`GET /retrieve_isolated_formula?latex=&top_k=`)

### API

- `GET /api/posts?offset=&limit=`, `GET /api/posts/{silver_id}`
- `GET /api/formulas?offset=&limit=`, `GET /api/formulas/{id}`
- `GET /api/formulas/{id}/graph` -- `{id, latex, opt: {available, annotated, svg}, slt: {available, svg}}`
- `GET /api/gold_formulas/{id}/graph` -- same shape as above, for a `gold.formula` id (raw OPT, never annotated)
- `GET /api/retrieval?latex=&top_k=` -- `{latex, results: [{rank, formula_id, score, latex}]}`; proxies `RETRIEVAL_URL` and joins `gold.formula` (always `gold`, independent of `PG_GOLD_SCHEMA`) for the LaTeX
- `GET /api/multimodal_retrieval?query=&top_k=` -- `{query, formulas, text_query, results: [{rank, silver_post_id, post_id, post_type_id, score, formula_score, text_score, text, content}]}`; proxies `RETRIEVAL_URL`, `content` is the post as text/formula segments from `silver` (null if the post isn't there)
- `GET /api/annotated_retrieval?query=&top_k=` -- `{query, query_formulas: [{latex, descriptors, annotations}], results: [{rank, formula_id, score, latex, annotations, silver_formula_id, arqmath_formula_id, gold_formula_id, visual_id, silver_post_id, post_id}]}`; proxies `retrieve_annotated_formula` as-is (the service already returns LaTeX and annotations)
- `GET /api/multimodal_retrieval_annotated?query=&top_k=` -- same shape as `/api/multimodal_retrieval`; proxies `retrieve_multimodal_posts_annotated`
- `GET /api/task1/topics`, `GET /api/task1/evaluate`, `GET /api/task1/topics/{topic_id}/results` -- passthrough (same params, status codes and JSON) to the retrieval service's ARQMath Task 1 API at `RETRIEVAL_URL/task1/...`; no read timeout on `evaluate` (it blocks for up to ~35 min)
- `GET /api/silver_formulas/{silver_id}/graph` -- same shape as `/api/formulas/{id}/graph`, for a `silver.formula_arqmath.silver_id` (always `silver`/`gold`, independent of `PG_SCHEMA`)
- `GET /api/vocab/{id}` -- the `public.vocab` row plus `dataset_name` (always `public`, independent of `PG_SCHEMA`)

## Frontend (React + Vite + Bootstrap)

```bash
cd webapp/frontend
npm install
npm run dev                 # http://localhost:5173, proxies /api to http://localhost:8000
```
