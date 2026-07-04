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
