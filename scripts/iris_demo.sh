#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"

cd "$REPO_ROOT"

docker compose run --rm iris_demo_seed
docker compose run --rm platform_bootstrap
docker compose run --rm iris_bootstrap
docker compose run --rm \
  -e DATASET_CONFIG_PATH=/datasets/iris/config.yaml \
  warehouse_loader
docker compose run --rm iris_transform
docker compose run --rm iris_train
