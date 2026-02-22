import os
import pandas as pd
import mlflow
import mlflow.sklearn
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.linear_model import LogisticRegression

def main():
    # Postgres (warehouse)
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.environ["POSTGRES_USER"]
    pw = os.environ["POSTGRES_PASSWORD"]
    db = os.environ["POSTGRES_DB"]

    feature_table = os.getenv("FEATURE_TABLE", "features.iris_features")
    target_col = os.getenv("TARGET_COL", "species")

    # MLflow
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "iris"))

    engine = create_engine(f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}")
    df = pd.read_sql(f"SELECT * FROM {feature_table}", engine)

    if target_col not in df.columns:
        raise ValueError(f"TARGET_COL='{target_col}' not in columns: {list(df.columns)}")

    X = df.drop(columns=[target_col])
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    with mlflow.start_run():
        mlflow.log_param("feature_table", feature_table)
        mlflow.log_param("target_col", target_col)
        mlflow.log_param("model", "LogisticRegression")

        model = LogisticRegression(max_iter=1000)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro")

        mlflow.log_metric("accuracy", float(acc))
        mlflow.log_metric("f1_macro", float(f1))

        mlflow.sklearn.log_model(model, "model")

if __name__ == "__main__":
    main()