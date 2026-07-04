CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.latex_arqmath (
    bronze_id     BIGSERIAL PRIMARY KEY,
    id            BIGINT,
    post_id       BIGINT,
    thread_id     BIGINT,
    type          TEXT,
    comment_id    BIGINT,
    old_visual_id BIGINT,
    visual_id     BIGINT,
    issue         TEXT,
    formula       TEXT,
    source_file   TEXT NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bronze.slt_arqmath (
    bronze_id     BIGSERIAL PRIMARY KEY,
    id            BIGINT,
    post_id       BIGINT,
    thread_id     BIGINT,
    type          TEXT,
    comment_id    BIGINT,
    old_visual_id BIGINT,
    visual_id     BIGINT,
    issue         TEXT,
    formula       TEXT,
    source_file   TEXT NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bronze.opt_arqmath (
    bronze_id     BIGSERIAL PRIMARY KEY,
    id            BIGINT,
    post_id       BIGINT,
    thread_id     BIGINT,
    type          TEXT,
    comment_id    BIGINT,
    old_visual_id BIGINT,
    visual_id     BIGINT,
    issue         TEXT,
    formula       TEXT,
    source_file   TEXT NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
