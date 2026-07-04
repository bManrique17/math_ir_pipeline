CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.formula_arqmath (
    silver_id             BIGSERIAL PRIMARY KEY,
    id                    BIGINT NOT NULL,
    visual_id             BIGINT,
    latex                 TEXT,
    p_mathml              TEXT,
    c_mathml              TEXT,
    fk_gold_formula       BIGINT,
    opt_nx_dict_annotated JSONB,
    ingested_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formula_arqmath_id ON {schema}.formula_arqmath (id);

CREATE TABLE IF NOT EXISTS {schema}.post_arqmath (
    silver_id                                     BIGSERIAL PRIMARY KEY,
    id                                             BIGINT NOT NULL,
    title                                          TEXT,
    body                                           TEXT,
    post_type_id                                   BIGINT,
    normalized_text_and_latex                      TEXT,
    normalized_text_placeholders_formula_id        TEXT,
    normalized_text_placeholders_visual_id         TEXT,
    formula_descriptors                            JSONB,
    normalized_text_placeholders_fk_gold_formula   TEXT,
    ingested_at                                    TIMESTAMPTZ NOT NULL DEFAULT now()
);
