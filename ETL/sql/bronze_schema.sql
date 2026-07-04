CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.latex_arqmath (
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
CREATE INDEX IF NOT EXISTS idx_latex_arqmath_id ON {schema}.latex_arqmath (id);

CREATE TABLE IF NOT EXISTS {schema}.slt_arqmath (
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
CREATE INDEX IF NOT EXISTS idx_slt_arqmath_id ON {schema}.slt_arqmath (id);

CREATE TABLE IF NOT EXISTS {schema}.opt_arqmath (
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
CREATE INDEX IF NOT EXISTS idx_opt_arqmath_id ON {schema}.opt_arqmath (id);

CREATE TABLE IF NOT EXISTS {schema}.post_arqmath (
    bronze_id                BIGSERIAL PRIMARY KEY,
    id                       BIGINT,
    post_type_id             BIGINT,
    accepted_answer_id       BIGINT,
    parent_id                BIGINT,
    creation_date            TIMESTAMPTZ,
    deletion_date            TIMESTAMPTZ,
    score                    BIGINT,
    view_count               BIGINT,
    body                     TEXT,
    owner_user_id            BIGINT,
    owner_display_name       TEXT,
    last_editor_user_id      BIGINT,
    last_editor_display_name TEXT,
    last_edit_date           TIMESTAMPTZ,
    last_activity_date       TIMESTAMPTZ,
    title                    TEXT,
    tags                     TEXT,
    answer_count             BIGINT,
    comment_count            BIGINT,
    favorite_count           BIGINT,
    closed_date              TIMESTAMPTZ,
    community_owned_date     TIMESTAMPTZ,
    content_license          TEXT,
    source_file              TEXT NOT NULL,
    ingested_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
