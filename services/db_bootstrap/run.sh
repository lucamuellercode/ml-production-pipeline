#!/bin/sh
set -eu

: "${POSTGRES_USER:?Missing POSTGRES_USER}"
: "${POSTGRES_PASSWORD:?Missing POSTGRES_PASSWORD}"
: "${POSTGRES_DB:?Missing POSTGRES_DB}"

export PGPASSWORD="$POSTGRES_PASSWORD"

SQL_DIR="${SQL_DIR:-/sql}"

echo "Waiting for Postgres..."
until pg_isready -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  sleep 1
done

echo "Looking for SQL files in: $SQL_DIR"

# Fail fast if no SQL files are present
if ! find "$SQL_DIR" -maxdepth 1 -type f -name '*.sql' -print -quit | grep -q .; then
  echo "ERROR: No .sql files found in $SQL_DIR" >&2
  echo "Hint: Check your docker-compose volume mount to /sql (and that the host folder contains *.sql)." >&2
  exit 1
fi

echo "Running SQL files..."
for f in "$SQL_DIR"/*.sql; do
  echo "Executing $f"
  psql -v ON_ERROR_STOP=1 -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
done

echo "Done."
