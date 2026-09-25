# ETL

Bronze/silver/gold pipeline over the ARQMath dataset (raw TSV formula dumps +
`posts.xml`) into Postgres, plus two extra passes that turn plain formulas
into descriptor-annotated OPT graphs for the [webapp](../webapp/README.md).

## Setup

```bash
docker compose -f ../services/docker/postgres.yaml up -d   # postgres_math_ir on :5432
make install                                                # conda env "etl" (python 3.12) + requirements.txt
conda activate etl
export PYTHONPATH=$PYTHONPATH:$(pwd)/..                     # repo root, so `lib.math_lib` imports resolve
```

`make reinstall` recreates the env from scratch if `requirements.txt` changes.

`extract-descriptors` additionally needs the `ollama` CLI on `PATH` (it
manages its own `ollama serve` process and pulls the model itself — no
separate setup beyond that).

## Running the pipeline

Each stage is a `make` target, run **in this order** — each one depends on
state the previous ones wrote:

```bash
make bronze              # raw TSV/XML -> bronze tables, 1:1
make silver              # bronze -> silver.formula_arqmath + silver.post_arqmath
make gold                # silver -> gold.formula (opt_nx_dict/slt_nx_dict); backfills silver.formula_arqmath.fk_gold_formula
make extract-descriptors # LLM-extracted formula_descriptors on silver.post_arqmath
make annotate-opt        # builds silver.formula_arqmath.opt_nx_dict_annotated
make update-silver-posts # fk_gold placeholders in post text
```

Ordering constraints:
- `silver`'s two sub-steps (formulas, then posts) always run together, formulas first — posts need the formula id -> visual_id map.
- `gold` must run before `extract-descriptors`, `annotate-opt`, and `update-silver-posts` (all three depend on `fk_gold_formula` and/or the gold formula table).
- `annotate-opt` must run after **both** `gold` (for the OPT trees) and `extract-descriptors` (for the sentences to annotate with) — it's what actually does the work described below.
- `update-silver-posts` only needs `gold`; its relative order vs. `extract-descriptors`/`annotate-opt` doesn't matter.

To re-run a single stage directly (e.g. against a non-default schema or chunk
size), call its `main_*.py` with Hydra overrides:

```bash
PYTHONPATH=.. python main_gold.py silver_schema_prefix=silver gold_schema_prefix=gold chunk_size=20000
```

### What `bronze` / `silver` / `gold` do

- **bronze**: raw TSVs (`latex`/`slt`/`opt` representations) and `posts.xml` loaded verbatim into `{bronze_schema}.{latex,slt,opt}_arqmath` and `{bronze_schema}.post_arqmath`. Truncate-and-reload, so idempotent.
- **silver**: `formula_arqmath` is a SQL join of the three bronze formula tables on `id`. `post_arqmath` strips HTML from title+body and derives placeholder-text variants (`normalized_text_and_latex`, `normalized_text_placeholders_formula_id`, `normalized_text_placeholders_visual_id`); `formula_descriptors` and `normalized_text_placeholders_fk_gold_formula` are left `NULL` here, filled in by later stages.
- **gold**: for each distinct `visual_id` in silver, converts P-MathML/C-MathML into SLT/OPT graphs (via `lib/math_lib`) and stores them as JSONB (`nx.node_link_data` format); rows where either conversion fails are dropped. Backfills `silver.formula_arqmath.fk_gold_formula` by `visual_id`.

### `extract-descriptors` — LLM formula descriptions

Reads `silver.post_arqmath` rows where `normalized_text_placeholders_formula_id`
is set and `formula_descriptors` is still `NULL`, and asks an LLM (via a
locally-managed Ollama server) to extract `(formula placeholder, description)`
pairs from the post text, writing `{formula_id_str: [sentence, ...]}` back into
`formula_descriptors`. Resumable — only unprocessed rows are selected by
default; pass `overwrite: true` (see config below) to reprocess everything.

### `annotate-opt` — post-context-aware OPT annotation

The step this pipeline was extended for. For every post, every formula it
references gets an annotated copy of its gold OPT tree: wherever a node's
subtree is *exactly* the same (same labels, same child order, with
commutative/`U!` operators treated as unordered) as the whole tree of some
formula in that same post that has descriptor sentences, a text node is
attached (edge direction: text node -> the math node it describes). This
covers both a formula's own direct annotation (its root always matches
itself) and propagation of a sentence onto every structurally identical
subexpression elsewhere in the post. Written into
`silver.formula_arqmath.opt_nx_dict_annotated`, one row per formula
*occurrence* (not per gold/visual_id formula), since the same gold formula can
appear in different posts with different sibling formulas/sentences and
therefore get a different annotated graph each time. Not incrementally
resumable — every run recomputes and overwrites every resolvable row, so it's
safe to just re-run whenever `gold` or `formula_descriptors` change upstream.

### `update-silver-posts`

Re-derives post text with gold formula ids as placeholders
(`normalized_text_placeholders_fk_gold_formula`), using the `fk_gold_formula`
backfilled by `gold`. Unresolved formulas become `-1`.

## Config (`conf/config.yaml`, Hydra)

| Key | Meaning |
|---|---|
| `db.postgres_connection_string` | Postgres DSN |
| `bronze_schema_prefix` / `silver_schema_prefix` / `gold_schema_prefix` | schema names each layer reads/writes (defaults are the `debug_*` schemas) |
| `bronze_load_formulas` / `bronze_load_posts` | toggle bronze sub-steps |
| `silver_load_formulas` / `silver_load_posts` | toggle silver sub-steps (posts needs formulas already loaded) |
| `gold_load_formulas` | toggle the gold step |
| `descriptors_load_formula_descriptors` | toggle `extract-descriptors` |
| `silver_load_opt_annotations` | toggle `annotate-opt` |
| `chunk_size` | batch size used by most stages for chunked reads/writes |
| `paths.raw_dir` / `paths.posts_path` | bronze source locations |
| `formula_sources` / `post_sources` | bronze table name <-> source path mapping |
| `silver_formula` / `silver_post` | which bronze table names silver reads from |
| `descriptors.ollama_model` | Ollama model tag (default `llama3.2:3b`) |
| `descriptors.ollama_gpu` | `CUDA_VISIBLE_DEVICES` index for the managed Ollama server |
| `descriptors.ollama_port` | port for the managed Ollama server (reused if already listening) |
| `descriptors.num_ctx` | LLM context window size |
| `descriptors.write_buffer_size` | rows buffered before flushing to Postgres |
| `descriptors.limit` | cap rows processed per run (`null` = no cap) |
| `descriptors.overwrite` | reprocess rows that already have `formula_descriptors` |

Override any key on the command line, Hydra-style: `key=value`, dotted for
nested keys (e.g. `descriptors.ollama_model=llama3.2:1b`).

## Other files

- `sql/{bronze,silver,gold}_schema.sql` — `CREATE SCHEMA`/`CREATE TABLE IF NOT EXISTS`, applied at the start of each corresponding stage.
- `etl/` — the actual per-stage logic; `main_*.py` are thin Hydra entry points around it.
- `bin/set_env.sh` — creates/updates the `etl` conda env (used by `make install`/`reinstall`).
