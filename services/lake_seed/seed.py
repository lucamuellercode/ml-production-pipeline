import os
from botocore.exceptions import ClientError
import boto3
import pandas as pd
from sklearn.datasets import load_iris


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing envrionment variable {name}")
    

def ensure_bucket(s3, bucket: str) -> None:

    existing = [b["Name"]for b in s3.list_buckets().get("Buckets", [])]
    if bucket in existing:
        return
    
    s3.create_bucket(Bucket=bucket)
    print(f"Created bucket: {bucket}")


def obejct_exist(s3, bucket: str, key: str)-> bool:
    try:
        s3.head_object(Bucket=bucket,Key=key)
        return True
    except ClientError as e:
        # 404 doesnt exist
        code = e.response.get("Error", {}).get("Code")
        return code in ("404", "NoSuchKey", "NotFound")
    

def main() ->None:
    endpoint_url = get_env("STORAGE_ENDPOINT_URL")
    acces_key = get_env("MINIO_ROOT_USER")
    secret_key= get_env("MINIO_ROOT_PASSWORD")

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_acces_key_id=acces_key,
        aws_secret_acces_key=secret_key,
        region_name="eu-west-1",
    )

    bucket = "dataset"
    key = "iris/v1/iris.csv"

    ensure_bucket(s3, bucket)

    if obejct_exist(s3,bucket,key)
        print(f"Object already exists: s3//{bucket}/{key} -> skipping")
        return
    

    iris = load_iris()
    df = pd.DataFrame(iris.data, columns=iris.feature_names)
    df["target"] = iris.target
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    #Upload

    s3.put_object(Bucket=bucket, Key=key, Body=csv_bytes, ContentType="text/csv")
    print("Uploaded: s3//{bucket}/{key}")



if __name__ == "__main__":
    main()