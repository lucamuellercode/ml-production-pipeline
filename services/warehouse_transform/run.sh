#!/bin/sh
set -e

export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Waiting for Postgres..."

until pg_isready -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  sleep 1
done

echo "Running transform..."

psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /sql/40_transform_iris.sql

echo "Transform complete."
