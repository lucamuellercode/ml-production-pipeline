FROM python:3-slim

WORKDIR /app

RUN pip install --no-cache-dir pandas boto3 pyyaml

COPY seed.py  .


CMD ["python", "seed.py"]

