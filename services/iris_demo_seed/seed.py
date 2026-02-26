import os
from dataclasses import dataclass
from pathlib import Path

import boto3
import pandas as pd
import yaml
from botocore.exceptions import ClientError
from sklearn.datasets import load_iris


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False

    raise RuntimeError(
        f"Invalid boolean for {name}: {raw!r}. Use one of true/false, 1/0, yes/no."
    )


@dataclass(frozen=True)
class DatasetContract:
    dataset_name: str
    version: str
    storage_bucket: str
    storage_key: str


def resolve_dataset_config_path() -> Path:
    return Path(os.getenv("DATASET_CONFIG_PATH", "/datasets/iris/config.yaml"))


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
    except KeyError as e:
        raise RuntimeError(f"Missing key in dataset config {path}: {e}") from e

    return DatasetContract(
        dataset_name=dataset_name,
        version=version,
        storage_bucket=storage_bucket,
        storage_key=storage_key,
    )


def ensure_bucket(s3, bucket: str) -> None:
    buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    if bucket in buckets:
        return
    s3.create_bucket(Bucket=bucket)
    print(f"Created bucket: {bucket}")


def object_exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def build_iris_dataframe() -> pd.DataFrame:
    iris = load_iris()
    df = pd.DataFrame(iris.data, columns=iris.feature_names)
    df["target"] = iris.target
    return df


def main() -> None:
    endpoint_url = env("STORAGE_ENDPOINT_URL")
    access_key = env("MINIO_ROOT_USER")
    secret_key = env("MINIO_ROOT_PASSWORD")
    overwrite = env_bool("SEED_OVERWRITE", default=False)

    contract_path = resolve_dataset_config_path()
    contract = load_dataset_contract(contract_path)
    bucket = os.getenv("DATASET_BUCKET", contract.storage_bucket)
    key = os.getenv("DATASET_KEY", contract.storage_key)

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )

    ensure_bucket(s3, bucket)
    exists = object_exists(s3, bucket, key)
    print(f"Dataset config: {contract_path}")
    print(f"Exists? {exists} -> s3://{bucket}/{key}")

    if exists and not overwrite:
        print("Skipping upload (already exists).")
        return

    if exists and overwrite:
        print("Overwriting existing object.")

    df = build_iris_dataframe()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=csv_bytes,
        ContentType="text/csv",
    )

    print(f"Uploaded Iris demo dataset to s3://{bucket}/{key}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()
