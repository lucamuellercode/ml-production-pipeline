import os
from pathlib import Path

import boto3
import pandas as pd
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


def build_default_iris_dataframe() -> pd.DataFrame:
    iris = load_iris()
    df = pd.DataFrame(iris.data, columns=iris.feature_names)
    df["target"] = iris.target
    return df


def read_local_csv(path_value: str) -> pd.DataFrame:
    path = Path(path_value)
    if not path.exists():
        raise RuntimeError(f"DATASET_LOCAL_PATH does not exist: {path}")
    if not path.is_file():
        raise RuntimeError(f"DATASET_LOCAL_PATH is not a file: {path}")
    return pd.read_csv(path)


def read_seed_dataframe(seed_mode: str) -> tuple[pd.DataFrame, str]:
    mode = seed_mode.strip().lower()
    if mode == "demo_iris":
        return build_default_iris_dataframe(), "sklearn.datasets.load_iris()"

    if mode == "local_csv":
        local_path = env("DATASET_LOCAL_PATH")
        return read_local_csv(local_path), local_path

    raise RuntimeError(
        f"Unsupported SEED_MODE={seed_mode!r}. Supported values: demo_iris, local_csv."
    )


def main() -> None:
    endpoint_url = env("STORAGE_ENDPOINT_URL")
    access_key = env("MINIO_ROOT_USER")
    secret_key = env("MINIO_ROOT_PASSWORD")

    seed_mode = os.getenv("SEED_MODE", "demo_iris")
    overwrite = env_bool("SEED_OVERWRITE", default=False)
    bucket = env("DATASET_BUCKET", "datasets")
    key = env("DATASET_KEY", "iris/v1/iris.csv")

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )

    ensure_bucket(s3, bucket)

    exists = object_exists(s3, bucket, key)
    print(f"Seed mode: {seed_mode}")
    print(f"Exists? {exists} -> s3://{bucket}/{key}")

    if exists and not overwrite:
        print("Skipping upload (already exists).")
        return

    df, source_label = read_seed_dataframe(seed_mode)
    if exists and overwrite:
        print("Overwriting existing object.")
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=csv_bytes,
        ContentType="text/csv",
    )

    print(f"Uploaded dataset to s3://{bucket}/{key}")
    print(f"Source: {source_label}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()
