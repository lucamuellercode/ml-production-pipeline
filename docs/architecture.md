# Architecture

## Runtime components

- `postgres`: warehouse + metadata + MLflow backend DB
- `minio`: S3-compatible object storage
- `mlflow` + `mlflow_proxy`: experiment tracking and model registry
- `lake_seed` (job): generic CSV seed from local file -> MinIO (dataset contract driven)
- `iris_demo_seed` (job): Iris-only demo data generator -> MinIO
- `platform_bootstrap` (job): creates global schemas/tables
- `iris_bootstrap` (job): creates dataset tables
- `warehouse_loader` (job): loads raw data from MinIO into `raw` schema (dataset contract driven)
- `iris_transform` (job): creates staging/features rows
- `iris_train` (job): trains model and logs to MLflow

## Postgres schema boundaries

- `raw`: immutable source-shaped data from object storage
- `staging`: cleaned/normalized dataset tables
- `features`: model-ready training/inference features
- `serving`: online-serving views and materialized tables
- `metadata`: dataset versions and ingestion audit records
- `mlops`: model quality, drift, and monitoring snapshots

## MinIO bucket boundaries

- `datasets`: versioned source files (`<dataset>/<version>/...`)
- `mlflow`: MLflow artifacts

Recommended next step as project grows:

- `lake-raw`: external source drops
- `lake-curated`: transformed files/parquet snapshots
- `models`: promoted model bundles for serving

## Data contracts

Dataset contracts live in `datasets/<name>/config.yaml`.

Each contract should define:

- storage location (`bucket`, `key`)
- warehouse table names
- target column and dropped columns
- required feature columns
- model training defaults
