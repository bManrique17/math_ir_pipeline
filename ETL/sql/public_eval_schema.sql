-- ARQMath evaluation topics and qrels (Task 1 and Task 2, ARQMath 1-3).
-- Topic ids already encode the version (A.1 / A.201 / A.301, ...), so they are
-- unique across versions.

CREATE TABLE IF NOT EXISTS public.topics_task1 (
    topic_id            TEXT PRIMARY KEY,
    raw_content         TEXT,
    normalized_content  TEXT,
    arqmath_version     SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.topics_task2 (
    topic_id            TEXT PRIMARY KEY,
    raw_content         TEXT,
    normalized_content  TEXT,
    formula_id          TEXT,
    formula_latex       TEXT,
    arqmath_version     SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.qrels_task1 (
    topic_id         TEXT NOT NULL,
    post_id          BIGINT NOT NULL,
    relevance        SMALLINT NOT NULL,
    arqmath_version  SMALLINT NOT NULL,
    PRIMARY KEY (topic_id, post_id)
);

CREATE TABLE IF NOT EXISTS public.qrels_task2_visual_id (
    topic_id         TEXT NOT NULL,
    visual_id        BIGINT NOT NULL,
    relevance        SMALLINT NOT NULL,
    arqmath_version  SMALLINT NOT NULL,
    PRIMARY KEY (topic_id, visual_id)
);

-- post_id is looked up from silver.formula_arqmath (id -> post_id); NULL when
-- the formula id is not in silver.
CREATE TABLE IF NOT EXISTS public.qrels_task2_formula_id (
    topic_id         TEXT NOT NULL,
    formula_id       BIGINT NOT NULL,
    relevance        SMALLINT NOT NULL,
    arqmath_version  SMALLINT NOT NULL,
    post_id          BIGINT,
    PRIMARY KEY (topic_id, formula_id)
);
