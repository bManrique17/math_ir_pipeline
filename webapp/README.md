# Formula Descriptors Viewer

Two tabs (top nav):

- **Posts** (`/`) — `{schema}.post_arqmath` rows: the post text (formulas
  rendered via MathJax) and, in one merged table, every formula referenced in
  that post alongside its extracted `formula_descriptors` sentences (one row
  per formula id, "Descriptions" column shows the sentences or "none"). Search
  by `silver_id` to jump to a single post.
- **Formulas** (`/formulas`) — all of `{schema}.formula_arqmath`, paginated.
  Two independent search bars: search by formula id, or filter to the formulas
  referenced by a given post id (reuses the Posts-tab post lookup under the
  hood).

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

### API

- `GET /api/posts?offset=&limit=`, `GET /api/posts/{silver_id}`
- `GET /api/formulas?offset=&limit=`, `GET /api/formulas/{id}`
- `GET /api/formulas/{id}/graph` -- `{id, latex, opt: {available, annotated, svg}, slt: {available, svg}}`

## Frontend (React + Vite + Bootstrap)

```bash
cd webapp/frontend
npm install
npm run dev                 # http://localhost:5173, proxies /api to http://localhost:8000
```
