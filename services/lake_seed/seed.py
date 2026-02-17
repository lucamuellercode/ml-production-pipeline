import os
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from sklearn.datasets import load_iris


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


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


def main() -> None:
    endpoint_url = env("STORAGE_ENDPOINT_URL")
    access_key = env("MINIO_ROOT_USER")
    secret_key = env("MINIO_ROOT_PASSWORD")

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
    print(f"Exists? {exists} -> s3://{bucket}/{key}")

    if exists:
        print("Skipping upload (already exists).")
        return

    # Default behavior: seed Iris demo dataset
    df = build_default_iris_dataframe()
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=csv_bytes,
        ContentType="text/csv",
    )

    print(f"Uploaded demo dataset to s3://{bucket}/{key}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()
