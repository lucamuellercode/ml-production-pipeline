# Learning Path

## 1. Foundations

Goal: understand raw -> staging -> features -> train.

Run:

1. `docker compose up -d postgres minio`
2. `./scripts/iris_demo.sh` (or `make iris_demo`)

Verify:

- `raw.iris` has raw source columns
- `staging.iris_clean` has normalized columns
- `features.iris_features` has training rows
- MLflow run has metrics + artifacts + model

## 2. MLOps basics

Goal: reproducibility and traceability.

Focus areas:

- deterministic split and model hyperparameters
- dataset version and load metadata
- experiment logging and artifacts

## 3. Reuse for a new dataset

1. Copy `datasets/TEMPLATE.config.yaml` to `datasets/<new_dataset>/config.yaml`
2. Add SQL files under:
   - `sql/datasets/<new_dataset>/tables/`
   - `sql/datasets/<new_dataset>/transforms/`
3. Add `<new_dataset>_bootstrap` and `<new_dataset>_transform` services in `docker-compose.yml`
4. Run `warehouse_loader` with overridden dataset env vars
5. Run trainer with overridden `FEATURE_TABLE` and `TARGET_COL`
