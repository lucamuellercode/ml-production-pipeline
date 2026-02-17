# ml-production-pipeline

A simple machine learning production pipeline, for now:


**This project starts a local ML infrastructure using Docker**:

- PostgreSQL → warehouse & metadata
- MinIO → object storage (local S3)
- lake_seed job → uploads a sample dataset


## How to run


--------------------------------
### 1) Prerequisites
--------------------------------


Install:

- Docker
- Docker Compose



--------------------------------
### 2) Create a .env file
--------------------------------

In the project root create a file named:

.env

Add the following content (replace passwords):
```.env
POSTGRES_SUPERUSER=warehouse_user
POSTGRES_SUPERPASS=your_strong_password
POSTGRES_DEFAULT_DB=warehouse

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_strong_password

STORAGE_ENDPOINT_URL=http://minio:9000
MLFLOW_S3_ENDPOINT_URL=${STORAGE_ENDPOINT_URL}
```


--------------------------------
####  3) Start the infrastructure
--------------------------------
```bash
docker compose up -d
docker compose ps
```

Services will be available at:

PostgreSQL:
localhost:5433

MinIO S3 API:
http://localhost:9000

MinIO Web UI:
http://localhost:9001



--------------------------------
### 4) Upload the dataset
--------------------------------

Build and run the seed job:

```bash 
docker compose build lake_seed
docker compose run --rm lake_seed
```

The job will:

- create bucket "datasets" if missing
- upload iris/v1/iris.csv
- skip upload if it already exists

--------------------------------
### 5) View the dataset
--------------------------------

Open the MinIO web interface:

http://localhost:9001

Login using credentials from .env.

Navigate to:

datasets → iris → v1 → iris.csv

--------------------------------
### 6) Stop the services
--------------------------------

Stop containers:

```bash
docker compose down

Reset everything (delete data):

docker compose down -v
```



# One-line Rebuild

```bash

docker compose down -v
docker compose up -d
docker compose run --rm lake_seed
docker compose run --rm db_bootstrap
docker compose run --rm warehouse_loader
docker compose run --rm warehouse_transform


```


├── docker-compose.yml
├── infra
│   └── postgres
│       ├── 00_platform
│       │   ├── 00_schemas.sql
│       │   └── 10_metadata_tables.sql
│       └── 10_datasets
│           └── iris
│               ├── tables
│               └── transforms
├── README.md
└── services
    ├── db_bootstrap
    │   ├── Dockerfile
    │   └── run.sh
    ├── lake_seed
    │   ├── Dockerfile
    │   └── seed.py
    ├── warehouse_loader
    │   ├── Dockerfile
    │   └── loader.py
    └── warehouse_transform
        ├── Dockerfile
        └── run.sh

13 directories, 12 files




    


