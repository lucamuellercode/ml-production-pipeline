import io
import os
import re
from dataclasses import dataclass
from pathlib import Path

import boto3
import pandas as pd
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL


def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


# Strict SQL identifier validation (schema/table names)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ident(name: str) -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid identifier {name!r}. Only [A-Za-z_][A-Za-z0-9_]* is allowed."
        )
    return name


def split_schema_table(qualified_table: str) -> tuple[str, str]:
    parts = qualified_table.split(".")
    if len(parts) != 2:
        raise RuntimeError(
            f"Expected '<schema>.<table>' in dataset config, got: {qualified_table!r}"
        )
    return ident(parts[0]), ident(parts[1])


@dataclass(frozen=True)
class DatasetContract:
    dataset_name: str
    version: str
    storage_bucket: str
    storage_key: str
    raw_schema: str
    raw_table: str


@dataclass(frozen=True)
class DatasetConfig:
    bucket: str
    key: str
    name: str
    version: str

    @property
    def source_uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


@dataclass(frozen=True)
class PostgresConfig:
    user: str
    password: str
    db: str
    host: str = "postgres"
    port: str = "5432"


def resolve_dataset_config_path() -> Path:
    explicit_path = os.getenv("DATASET_CONFIG_PATH")
    if explicit_path:
        return Path(explicit_path)

    dataset_name = os.getenv("DATASET_NAME")
    if dataset_name:
        return Path(f"/datasets/{dataset_name}/config.yaml")

    raise RuntimeError("Set DATASET_CONFIG_PATH or DATASET_NAME for warehouse_loader.")


def load_dataset_contract(path: Path) -> DatasetContract:
    if not path.exists():
        raise RuntimeError(f"Dataset config not found: {path}")
    if not path.is_file():
        raise RuntimeError(f"Dataset config path is not a file: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    try:
        dataset_name = str(raw["dataset_name"])
        version = str(raw["version"])
        storage_bucket = str(raw["storage"]["bucket"])
        storage_key = str(raw["storage"]["key"])
        raw_table_qualified = str(raw["warehouse"]["raw_table"])
    except KeyError as e:
        raise RuntimeError(f"Missing key in dataset config {path}: {e}") from e

    raw_schema, raw_table = split_schema_table(raw_table_qualified)
    return DatasetContract(
        dataset_name=dataset_name,
        version=version,
        storage_bucket=storage_bucket,
        storage_key=storage_key,
        raw_schema=raw_schema,
        raw_table=raw_table,
    )


def make_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=env("STORAGE_ENDPOINT_URL"),
        aws_access_key_id=env("MINIO_ROOT_USER"),
        aws_secret_access_key=env("MINIO_ROOT_PASSWORD"),
        region_name="us-east-1",
    )


def read_csv_from_s3(s3, bucket: str, key: str) -> pd.DataFrame:
    obj = s3.get_object(Bucket=bucket, Key=key)
    csv_bytes = obj["Body"].read()
    return pd.read_csv(io.BytesIO(csv_bytes))


def make_engine(pg: PostgresConfig) -> Engine:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=pg.user,
        password=pg.password,
        host=pg.host,
        port=int(pg.port),
        database=pg.db,
    )
    return create_engine(url)


def truncate_raw_table(engine: Engine, schema: str, table: str) -> None:
    schema = ident(schema)
    table = ident(table)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {schema}.{table};"))


def load_dataframe_to_raw(engine: Engine, df: pd.DataFrame, schema: str, table: str) -> None:
    schema = ident(schema)
    table = ident(table)
    df.to_sql(table, engine, schema=schema, if_exists="append", index=False)


def upsert_dataset_metadata(engine: Engine, cfg: DatasetConfig, row_count: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO metadata.datasets (name, version, source_uri, row_count)
                VALUES (:name, :version, :source_uri, :row_count)
                ON CONFLICT (name, version)
                DO UPDATE SET
                  source_uri = EXCLUDED.source_uri,
                  row_count  = EXCLUDED.row_count,
                  loaded_at  = now();
                """
            ),
            {
                "name": cfg.name,
                "version": cfg.version,
                "source_uri": cfg.source_uri,
                "row_count": row_count,
            },
        )


def read_dataset_config(contract: DatasetContract) -> DatasetConfig:
    return DatasetConfig(
        bucket=os.getenv("DATASET_BUCKET", contract.storage_bucket),
        key=os.getenv("DATASET_KEY", contract.storage_key),
        name=os.getenv("DATASET_NAME", contract.dataset_name),
        version=os.getenv("DATASET_VERSION", contract.version),
    )


def read_postgres_config() -> PostgresConfig:
    return PostgresConfig(
        user=env("POSTGRES_USER"),
        password=env("POSTGRES_PASSWORD"),
        db=env("POSTGRES_DB"),
        host=env("POSTGRES_HOST", "postgres"),
        port=env("POSTGRES_PORT", "5432"),
    )


def read_raw_target(contract: DatasetContract) -> tuple[str, str]:
    raw_schema = env("RAW_SCHEMA", contract.raw_schema)
    raw_table = env("RAW_TABLE", contract.raw_table)
    return ident(raw_schema), ident(raw_table)


def main() -> None:
    contract_path = resolve_dataset_config_path()
    contract = load_dataset_contract(contract_path)
    ds = read_dataset_config(contract)
    pg = read_postgres_config()
    raw_schema, raw_table = read_raw_target(contract)

    s3 = make_s3_client()
    df = read_csv_from_s3(s3, ds.bucket, ds.key)

    engine = make_engine(pg)
    truncate_raw_table(engine, schema=raw_schema, table=raw_table)
    load_dataframe_to_raw(engine, df, schema=raw_schema, table=raw_table)
    upsert_dataset_metadata(engine, ds, row_count=len(df))

    print(f"Dataset config: {contract_path}")
    print(f"Loaded {len(df)} rows into {raw_schema}.{raw_table}")
    print(f"Upserted metadata for {ds.name}:{ds.version} ({ds.source_uri})")


if __name__ == "__main__":
    main()
