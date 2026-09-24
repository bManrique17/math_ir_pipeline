# Formula Descriptors Viewer

Visualizes `{schema}.post_arqmath` rows: the post text (formulas rendered via
MathJax), the formulas referenced in that post (id + rendered LaTeX), and the
extracted `formula_descriptors` for each formula id.

## Backend (FastAPI)

```bash
cd webapp/backend
bash setup_env.sh          # creates conda env "webapp_backend", installs requirements.txt
conda activate webapp_backend
uvicorn app.main:app --reload --port 8000
```

Configurable via env vars (defaults match `ETL/conf/config.yaml`):
- `PG_DSN` (default `postgresql://postgres:postgres@localhost:5432/math_ir`)
- `PG_SCHEMA` (default `debug_silver`)

## Frontend (React + Vite + Bootstrap)

```bash
cd webapp/frontend
npm install
npm run dev                 # http://localhost:5173, proxies /api to http://localhost:8000
```
