# ml-production-pipeline

Reusable local ML pipeline template for learning and demos.

It shows a full lifecycle:

- ingest dataset from object storage
- load and transform in warehouse
- train and evaluate model
- track runs and artifacts in MLflow

## Golden path

```text
MinIO (datasets) -> warehouse_loader -> Postgres raw
Postgres raw -> iris_transform -> Postgres staging/features
Postgres features -> iris_train -> MLflow metrics/artifacts/model
```

## Repository layout

```text
.
├── datasets/
│   ├── iris/config.yaml
│   └── TEMPLATE.config.yaml
├── docs/
│   ├── architecture.md
│   └── learning-path.md
├── infra/
│   ├── minio/
│   ├── nginx/
│   └── postgres/init/
├── services/
│   ├── db_bootstrap/
│   ├── iris_demo_seed/
│   ├── iris_train/
│   ├── lake_seed/
│   └── warehouse_loader/
├── scripts/
│   └── iris_demo.sh
├── Makefile
├── sql/
│   ├── platform/
│   └── datasets/iris/
│       ├── tables/
│       └── transforms/
├── docker-compose.yml
└── README.md
```

## Environment

Create `.env` from `.env.example` and set passwords.

```env
POSTGRES_SUPERUSER=warehouse_user
POSTGRES_SUPERPASS=your_strong_password
POSTGRES_DEFAULT_DB=warehouse

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_strong_password

STORAGE_ENDPOINT_URL=http://minio:9000
MLFLOW_S3_ENDPOINT_URL=${STORAGE_ENDPOINT_URL}
MLFLOW_DB=mlflow
MLFLOW_DB_USER=mlflow_user
MLFLOW_DB_PASS=your_strong_password
GIT_PYTHON_REFRESH=quiet

SEED_OVERWRITE=false
# DATASET_CONFIG_PATH=/datasets/your_dataset/config.yaml
# DATASET_LOCAL_PATH=/datasets/your_dataset/data.csv

DATASET_NAME=iris
DATASET_VERSION=v1
FEATURE_TABLE=features.iris_features
TARGET_COL=target
DROP_COLUMNS=row_id
MLFLOW_EXPERIMENT=iris
REGISTERED_MODEL_NAME=IrisClassifier
```

## Run the end-to-end Iris pipeline

1. Start platform services:

```bash
docker compose up -d postgres minio minio_init mlflow mlflow_proxy
```

2. Run the Iris demo job:

```bash
./scripts/iris_demo.sh
# or: make iris_demo
```

Equivalent manual sequence:

```bash
docker compose run --rm iris_demo_seed
docker compose run --rm platform_bootstrap
docker compose run --rm iris_bootstrap
docker compose run --rm -e DATASET_CONFIG_PATH=/datasets/iris/config.yaml warehouse_loader
docker compose run --rm iris_transform
docker compose run --rm iris_train
```

3. Verify:

- MLflow UI: `http://localhost:5001`
- MinIO UI: `http://localhost:9001`
- Postgres tables: `raw.iris`, `staging.iris_clean`, `features.iris_features`, `metadata.datasets`

## Iris API (FastAPI + Pydantic)

The demo API lives in `services/iris_api` and supports:

- `GET /health`
- `GET /model-info`
- `POST /predict`

Model selection is controlled via `MODEL_URI` at startup:

- empty/unset `MODEL_URI` -> dummy mode (always predicts `0`)
- set `MODEL_URI` (for example `models:/IrisClassifier/1`) -> load from MLflow

Run API service:

```bash
docker compose up -d iris_api
```

Load a specific registered model version:

```bash
IRIS_API_MODEL_URI=models:/IrisClassifier/1 docker compose up -d iris_api
```

Test:

```bash
curl http://localhost:8002/model-info

curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "sepal_length_cm": 5.1,
        "sepal_width_cm": 3.5,
        "petal_length_cm": 1.4,
        "petal_width_cm": 0.2
      }
    ]
  }'
```

## Dataset contracts in generic jobs

- `lake_seed` and `warehouse_loader` read `datasets/<name>/config.yaml` via:
  - `DATASET_CONFIG_PATH` (explicit), or
  - `DATASET_NAME` (`/datasets/<DATASET_NAME>/config.yaml`)
- Generic jobs are dataset-agnostic and contain no Iris-specific defaults.
- `iris_demo_seed` is the only job that contains Iris demo logic.

## SQL organization

- Platform SQL: `sql/platform`
- Dataset SQL: `sql/datasets/<dataset>/tables` and `sql/datasets/<dataset>/transforms`

Naming convention:

- `10_*` raw definitions
- `20_*` staging definitions
- `30_*` features definitions
- `40_*` raw -> staging transforms
- `50_*` staging -> features transforms

## Training service design

`services/iris_train` is now modular:

- `config.py`: typed env/config contract
- `data_sources.py`: data loading adapters
- `pipeline.py`: feature prep, split, train, evaluate
- `artifacts.py`: confusion matrix/report/histogram artifacts
- `mlflow_logger.py`: MLflow integration only
- `train.py`: orchestration entrypoint

This structure is intended to be copied for new datasets/models.

## Add a new dataset

Use this walkthrough for a new dataset, example: `cars`.

1. Create dataset config

```bash
mkdir -p datasets/cars
cp datasets/TEMPLATE.config.yaml datasets/cars/config.yaml
```

`lake_seed` and `warehouse_loader` use this config as the primary source for storage/raw table metadata.

2. Add SQL folders

```bash
mkdir -p sql/datasets/cars/tables
mkdir -p sql/datasets/cars/transforms
```

3. Add table SQL (example)

`sql/datasets/cars/tables/10_raw_cars.sql`

```sql
CREATE TABLE IF NOT EXISTS raw.cars (
  brand TEXT,
  model TEXT,
  horsepower DOUBLE PRECISION,
  mpg DOUBLE PRECISION,
  target INTEGER
);
```

`sql/datasets/cars/tables/20_staging_cars.sql`

```sql
CREATE TABLE IF NOT EXISTS staging.cars_clean (
  brand TEXT,
  model TEXT,
  horsepower DOUBLE PRECISION,
  mpg DOUBLE PRECISION,
  target INTEGER
);
```

`sql/datasets/cars/tables/30_features_cars.sql`

```sql
CREATE TABLE IF NOT EXISTS features.cars_features (
  row_id BIGSERIAL PRIMARY KEY,
  horsepower DOUBLE PRECISION,
  mpg DOUBLE PRECISION,
  target INTEGER
);
```

4. Add transform SQL (example)

`sql/datasets/cars/transforms/40_raw_to_staging_cars.sql`

```sql
TRUNCATE TABLE staging.cars_clean;

INSERT INTO staging.cars_clean (brand, model, horsepower, mpg, target)
SELECT brand, model, horsepower, mpg, target
FROM raw.cars;
```

`sql/datasets/cars/transforms/50_staging_to_features_cars.sql`

```sql
TRUNCATE TABLE features.cars_features;

INSERT INTO features.cars_features (horsepower, mpg, target)
SELECT horsepower, mpg, target
FROM staging.cars_clean;
```

5. Upload dataset file to MinIO

Option A: upload manually in MinIO UI (`http://localhost:9001`) to:

- bucket: `datasets`
- object key: `cars/v1/cars.csv`

Option B: use `lake_seed` with dataset contract + local CSV:

```bash
docker compose run --rm \
  -e DATASET_CONFIG_PATH=/datasets/cars/config.yaml \
  -e DATASET_LOCAL_PATH=/datasets/cars/cars.csv \
  lake_seed
```

6. Add Compose jobs for dataset SQL

Add these services to `docker-compose.yml`:

```yaml
cars_bootstrap:
  build: ./services/db_bootstrap
  entrypoint: ["/app/run.sh"]
  environment:
    POSTGRES_USER: ${POSTGRES_SUPERUSER}
    POSTGRES_PASSWORD: ${POSTGRES_SUPERPASS}
    POSTGRES_DB: ${POSTGRES_DEFAULT_DB}
  volumes:
    - ./sql/datasets/cars/tables:/sql:ro
  depends_on:
    - postgres

cars_transform:
  build: ./services/db_bootstrap
  entrypoint: ["/app/run.sh"]
  environment:
    POSTGRES_USER: ${POSTGRES_SUPERUSER}
    POSTGRES_PASSWORD: ${POSTGRES_SUPERPASS}
    POSTGRES_DB: ${POSTGRES_DEFAULT_DB}
  volumes:
    - ./sql/datasets/cars/transforms:/sql:ro
  depends_on:
    - postgres
    - cars_bootstrap
    - warehouse_loader
```

7. Run loader with dataset contract

```bash
docker compose run --rm \
  -e DATASET_CONFIG_PATH=/datasets/cars/config.yaml \
  warehouse_loader
```

8. Run dataset transforms

```bash
docker compose run --rm cars_bootstrap
docker compose run --rm cars_transform
```

9. Train with overrides

```bash
docker compose run --rm \
  -e FEATURE_TABLE=features.cars_features \
  -e TARGET_COL=target \
  iris_train
```

## Next planned extensions

- Prefect orchestration for scheduled/data-aware runs
- FastAPI serving service
- Prometheus + Grafana observability stack
- Optuna hyperparameter tuning
- More complex datasets and models (e.g. image classification with CNN)
  - Cloud deployments (e.g. AWS Sagemaker or GCP AI Platform) for training and serving?!
- CI/CD pipeline for automated testing and deployment
-  DVCS integration (e.g. DVC or Git LFS) for dataset versioning and management
