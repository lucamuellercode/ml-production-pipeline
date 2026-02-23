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
│   ├── iris_train/
│   ├── lake_seed/
│   └── warehouse_loader/
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

2. Run one-shot jobs in order:

```bash
docker compose run --rm lake_seed
docker compose run --rm platform_bootstrap
docker compose run --rm iris_bootstrap
docker compose run --rm warehouse_loader
docker compose run --rm iris_transform
docker compose run --rm iris_train
```

3. Verify:

- MLflow UI: `http://localhost:5001`
- MinIO UI: `http://localhost:9001`
- Postgres tables: `raw.iris`, `staging.iris_clean`, `features.iris_features`, `metadata.datasets`

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

1. Copy `datasets/TEMPLATE.config.yaml` -> `datasets/<name>/config.yaml`
2. Add SQL files:
   - `sql/datasets/<name>/tables/*.sql`
   - `sql/datasets/<name>/transforms/*.sql`
3. Add compose services `<name>_bootstrap` and `<name>_transform`
4. Run loader with overrides:

```bash
docker compose run --rm \
  -e DATASET_NAME=<name> \
  -e DATASET_KEY=<name>/v1/data.csv \
  -e RAW_TABLE=<name> \
  warehouse_loader
```

5. Train with overrides:

```bash
docker compose run --rm \
  -e FEATURE_TABLE=features.<name>_features \
  -e TARGET_COL=target \
  iris_train
```

## Next planned extensions

- Prefect orchestration for scheduled/data-aware runs
- FastAPI serving service
- Prometheus + Grafana observability stack
