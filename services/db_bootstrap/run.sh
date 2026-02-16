#!/bin/sh

set -e

export PGPPASSWORD="$POSTGRES_PASSWORD"

echo "Waiting for Postgres..."
until pg_isready -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  sleep 1
done

echo "Running SQL files..."
for f in /sql/*.sql; do
  echo "Executing $f"
  psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
done

echo "Done."
