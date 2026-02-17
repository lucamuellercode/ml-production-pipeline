import os
import io
import re
from dataclasses import dataclass

import boto3
import pandas as pd
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

    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
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
    # schema/table must be validated identifiers (avoid SQL injection).
    schema = ident(schema)
    table = ident(table)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {schema}.{table};"))


def load_dataframe_to_raw(engine: Engine, df: pd.DataFrame, schema: str, table: str) -> None:
    # df.to_sql uses SQLAlchemy safely for table creation/inserts, but schema/table still
    # come from config -> validate identifiers.
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


def read_dataset_config() -> DatasetConfig:
    return DatasetConfig(
        bucket=env("DATASET_BUCKET", "datasets"),
        key=env("DATASET_KEY", "iris/v1/iris.csv"),
        name=env("DATASET_NAME", "iris"),
        version=env("DATASET_VERSION", "v1"),
    )


def read_postgres_config() -> PostgresConfig:
    return PostgresConfig(
        user=env("POSTGRES_USER"),
        password=env("POSTGRES_PASSWORD"),
        db=env("POSTGRES_DB"),
        host=env("POSTGRES_HOST", "postgres"),
        port=env("POSTGRES_PORT", "5432"),
    )


def read_raw_target() -> tuple[str, str]:
    """
    Where to load the dataframe in the warehouse.
    Defaults:
      RAW_SCHEMA = "raw"
      RAW_TABLE  = DATASET_NAME
    """
    raw_schema = env("RAW_SCHEMA", "raw")
    raw_table = env("RAW_TABLE", env("DATASET_NAME", "iris"))
    return ident(raw_schema), ident(raw_table)


def main() -> None:
    ds = read_dataset_config()
    pg = read_postgres_config()
    raw_schema, raw_table = read_raw_target()

    s3 = make_s3_client()
    df = read_csv_from_s3(s3, ds.bucket, ds.key)

    engine = make_engine(pg)

    truncate_raw_table(engine, schema=raw_schema, table=raw_table)
    load_dataframe_to_raw(engine, df, schema=raw_schema, table=raw_table)

    upsert_dataset_metadata(engine, ds, row_count=len(df))

    print(f"Loaded {len(df)} rows into {raw_schema}.{raw_table}")
    print(f"Upserted metadata for {ds.name}:{ds.version} ({ds.source_uri})")


if __name__ == "__main__":
    main()
