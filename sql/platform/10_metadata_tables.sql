CREATE TABLE IF NOT EXISTS metadata.datasets (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    row_count INTEGER,
    loaded_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

