

# A docker file to ingest data from minio data 


FROM python:3-slim

WORKDIR /app

RUN pip install --no-cache-dir pandas boto3 sqlalchemy psycopg2-binary

COPY loader.py .


CMD ["python", "loader.py"]