#!/usr/bin/env bash
set -euo pipefail

echo "Initializing MLflow DB/user..."

: "${POSTGRES_USER:?}"
: "${POSTGRES_DB:?}"
: "${MLFLOW_DB:?}"
: "${MLFLOW_DB_USER:?}"
: "${MLFLOW_DB_PASS:?}"

# role
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${MLFLOW_DB_USER}') THEN
    CREATE ROLE ${MLFLOW_DB_USER} LOGIN PASSWORD '${MLFLOW_DB_PASS}';
  ELSE
    ALTER ROLE ${MLFLOW_DB_USER} WITH PASSWORD '${MLFLOW_DB_PASS}';
  END IF;
END
\$\$;
SQL

# db (CREATE DATABASE kann nicht in DO laufen)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -tAc \
  "SELECT 1 FROM pg_database WHERE datname='${MLFLOW_DB}'" | grep -q 1 \
  || psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c \
  "CREATE DATABASE ${MLFLOW_DB} OWNER ${MLFLOW_DB_USER};"