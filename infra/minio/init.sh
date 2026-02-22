#!/bin/sh
set -e

# Defaults, falls env nicht gesetzt ist
ENDPOINT="${STORAGE_ENDPOINT_URL:-http://minio:9000}"
ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}"
SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}"

echo "Waiting for MinIO at $ENDPOINT..."
until mc alias set local "$ENDPOINT" "$ACCESS_KEY" "$SECRET_KEY" >/dev/null 2>&1; do
  sleep 2
done

echo "Creating buckets..."
mc mb -p local/mlflow   >/dev/null 2>&1 || true
mc mb -p local/datasets >/dev/null 2>&1 || true

echo "Buckets:"
mc ls local