CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.formula (
    id                  BIGSERIAL PRIMARY KEY,
    visual_id           BIGINT NOT NULL UNIQUE,
    latex               TEXT,
    p_mathml            TEXT,
    c_mathml            TEXT,
    slt_nx_dict         JSONB,
    opt_nx_dict         JSONB,
    tangent_string_slt  TEXT,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formula_visual_id ON {schema}.formula (visual_id);
