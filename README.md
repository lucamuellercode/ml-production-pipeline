# ml-production-pipeline

A simple, reproducible machine learning production pipeline template (using **Iris** as the minimal example).

This repository starts a **local ML infrastructure using Docker**:

- **PostgreSQL** → warehouse (raw/staging/features) + metadata
- **MinIO** → object storage (local S3)
- **lake_seed** job → uploads a sample dataset to MinIO (defaults to Iris)

> **Important:** In this template, **Postgres + MinIO** are long-running services.  
> Everything else (`*_bootstrap`, `warehouse_loader`, `*_transform`, `lake_seed`) are **one-shot jobs** that should be executed **sequentially**.

---


## Repository layout (current)

```
├── docker-compose.yml
├── infra
│   ├── minio
│   │   └── init.sh
│   ├── nginx
│   │   └── mlflow.conf
│   └── postgres
│       ├── 00_platform
│       │   ├── 00_schemas.sql
│       │   └── 10_metadata_tables.sql
│       ├── 10_datasets
│       │   └── iris
│       │       ├── tables
│       │       │   ├── 20_raw_iris.sql
│       │       │   └── 30_staging_iris.sql
│       │       └── transforms
│       │           ├── 40_transform_iris.sql
│       │           └── 50_features_iris.sql
│       └── init
│           └── 05_create_mlflow_db.sh
├── README.md
└── services
    ├── db_bootstrap
    │   ├── Dockerfile
    │   └── run.sh
    ├── iris_train
    │   ├── Dockerfile
    │   └── train.py
    ├── lake_seed
    │   ├── Dockerfile
    │   └── seed.py
    └── warehouse_loader
        ├── Dockerfile
        └── loader.py

```

---



## How to run (Iris example)

### 1) Prerequisites

Install:

- Docker
- Docker Compose

---

### 2) Create a `.env` file

In the project root create a file named:

`./.env`

Add the following content (replace passwords):

```env
POSTGRES_SUPERUSER=warehouse_user
POSTGRES_SUPERPASS=your_strong_password
POSTGRES_DEFAULT_DB=warehouse

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_strong_password

STORAGE_ENDPOINT_URL=http://minio:9000
MLFLOW_S3_ENDPOINT_URL=${STORAGE_ENDPOINT_URL}
```

---

### 3) Start the infrastructure

Start only the infrastructure services:

```bash
docker compose up -d postgres minio
docker compose ps
```

Services will be available at:

**PostgreSQL:** `localhost:5433`  
**MinIO S3 API:** `http://localhost:9000`  
**MinIO Web UI:** `http://localhost:9001`

---

### 4) Upload the dataset (Iris demo)

Build & run the seed job:

```bash
docker compose build lake_seed
docker compose run --rm lake_seed
```

The job will:

- create bucket **datasets** if missing
- upload **iris/v1/iris.csv**
- skip upload if it already exists

---

### 5) Bootstrap the database (schemas + tables)

These are run as **jobs** (one-shot). Run them **in order**:

```bash
docker compose build platform_bootstrap
docker compose run --rm platform_bootstrap

docker compose build iris_bootstrap
docker compose run --rm iris_bootstrap
```

What this does:

- `platform_bootstrap` creates global schemas and metadata tables
- `iris_bootstrap` creates dataset-specific tables for Iris (e.g. `raw.iris`, `staging.iris_clean`)

---

### 6) Load raw data into Postgres

Run the loader job:

```bash
docker compose build warehouse_loader
docker compose run --rm warehouse_loader
```

Default configuration loads:

- `s3://datasets/iris/v1/iris.csv` → `raw.iris`

The loader is dataset-agnostic via env vars:

- `DATASET_BUCKET` (default: `datasets`)
- `DATASET_KEY` (default: `iris/v1/iris.csv`)
- `DATASET_NAME` (default: `iris`)
- `DATASET_VERSION` (default: `v1`)
- `RAW_SCHEMA` (default: `raw`)
- `RAW_TABLE` (default: `${DATASET_NAME}`)

---

### 7) Run transforms (raw → staging/features)

Run the transform job:

```bash
docker compose build iris_transform
docker compose run --rm iris_transform
```

This executes all SQL files mounted into `/sql` from:

```
infra/postgres/10_datasets/iris/transforms/
```

---

### 8) View the dataset in MinIO

Open the MinIO web interface:

`http://localhost:9001`

Login using credentials from `.env`.

Navigate to:

`datasets → iris → v1 → iris.csv`

---

### 9) Stop the services

Stop containers:

```bash
docker compose down
```

Reset everything (delete data):

```bash
docker compose down -v
```

---

## One-line rebuild (Iris)

This is the deterministic “clean rebuild” flow:

```bash
docker compose down -v
docker compose up -d postgres minio
docker compose run --rm lake_seed
docker compose run --rm platform_bootstrap
docker compose run --rm iris_bootstrap
docker compose run --rm warehouse_loader
docker compose run --rm iris_transform
```

> Transforms are executed via the generic SQL runner (`db_bootstrap`) using the dataset-specific service e.g. :`iris_transform`.

@Todo: In the future we can add profiles to `docker-compose.yml` to group related services and simplify this flow.
---

## Adding a new dataset (example: `cars`)

The template expects each dataset to provide:

- SQL to create raw/staging tables
- SQL transforms (raw → staging/features)
- A loader configuration (S3 key + target raw table)

### 1) Add SQL folders

Create:

```
infra/postgres/10_datasets/cars/
  tables/
  transforms/
```

Add your SQL files (example naming):

- `infra/postgres/10_datasets/cars/tables/20_raw_cars.sql`
- `infra/postgres/10_datasets/cars/tables/30_staging_cars.sql`
- `infra/postgres/10_datasets/cars/transforms/40_transform_cars.sql`

> Use numeric prefixes (`20_`, `30_`, `40_`) to control execution order.

---

### 2) Add dataset services to `docker-compose.yml`

Add two new job services (copy from `iris_bootstrap` / `iris_transform` and adjust mounts):

```yaml
cars_bootstrap:
  build: ./services/db_bootstrap
  entrypoint: ["/app/run.sh"]
  environment:
    POSTGRES_USER: ${POSTGRES_SUPERUSER}
    POSTGRES_PASSWORD: ${POSTGRES_SUPERPASS}
    POSTGRES_DB: ${POSTGRES_DEFAULT_DB}
  volumes:
    - ./infra/postgres/10_datasets/cars/tables:/sql:ro
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
    - ./infra/postgres/10_datasets/cars/transforms:/sql:ro
  depends_on:
    - postgres
    - cars_bootstrap
    - warehouse_loader
```

---

### 3) Upload your dataset to MinIO

Option A: upload via MinIO UI or `mc` client to a key like:

- `cars/v1/cars.csv`

Option B: reuse `lake_seed` by overriding env vars (still produces Iris by default, but key/bucket are configurable):

```bash
docker compose run --rm   -e DATASET_BUCKET=datasets   -e DATASET_KEY=cars/v1/cars.csv   lake_seed
```

@Todo: In the future we will create am more generic seed job that can support different datasets more easily. 

---

### 4) Run the new dataset pipeline

```bash
docker compose run --rm platform_bootstrap
docker compose run --rm cars_bootstrap

docker compose run --rm   -e DATASET_NAME=cars   -e DATASET_KEY=cars/v1/cars.csv   -e RAW_TABLE=cars   warehouse_loader

docker compose run --rm cars_transform
```

---


## Notes / conventions

- `services/db_bootstrap` is the **generic SQL runner**:
  - It executes all `*.sql` in `/sql`
  - It fails fast if `/sql` is empty (so missing mounts are caught immediately)
- Dataset-specific behavior lives in:
  - `infra/postgres/10_datasets/<dataset>/tables/`
  - `infra/postgres/10_datasets/<dataset>/transforms/`
- Loader is configured via environment variables and writes to `raw.<dataset>` by default.


---


# TL;DR

```bash
# ===============================
# 1) Alles sauber down (inkl. Volumes)
# ===============================
docker compose down -v --remove-orphans

# Optional: auch ungenutzte Images entfernen
docker image prune -f


# ===============================
# 2) Alles sauber up (richtige Reihenfolge)
# ===============================

# A) Basisdienste starten (Postgres + MinIO)
docker compose up -d postgres minio

# Status prüfen (warten bis Postgres "healthy")
docker compose ps


# B) MinIO Buckets anlegen (mlflow + datasets)
# Wichtig, sonst: NoSuchBucket-Fehler
docker compose run --rm -T minio_init


# C) MLflow starten (+ optional Proxy)
docker compose up -d mlflow mlflow_proxy

# Health Check
curl -I http://localhost:5000/health
# falls über Proxy/Nginx:
curl -I http://localhost:80/health


# D) Warehouse / SQL Schritte
docker compose run --rm platform_bootstrap
docker compose run --rm iris_bootstrap
docker compose run --rm warehouse_loader
docker compose run --rm iris_transform


# E) Training starten (erstellt neuen Run)
docker compose run --rm iris_train

```