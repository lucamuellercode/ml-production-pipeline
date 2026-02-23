FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    mlflow \
    pandas \
    sqlalchemy \
    psycopg2-binary \
    scikit-learn \
    boto3 \
    matplotlib

COPY train.py /app/train.py
CMD ["python", "/app/train.py"]
