import os
import json
import numpy as np
import pandas as pd

import mlflow
import mlflow.sklearn

from sqlalchemy import create_engine

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
from sklearn.linear_model import LogisticRegression

import matplotlib.pyplot as plt


def save_confusion_matrix_png(cm, class_names, path):
    fig = plt.figure()
    plt.imshow(cm)
    plt.xticks(range(len(class_names)), class_names, rotation=45, ha="right")
    plt.yticks(range(len(class_names)), class_names)
    plt.xlabel("Predicted")
    plt.ylabel("True")

    # numbers
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center")

    plt.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_confidence_histogram(y_proba_max, path):
    fig = plt.figure()
    plt.hist(y_proba_max, bins=20)
    plt.xlabel("Top-1 predicted probability")
    plt.ylabel("Count")
    plt.title("Prediction confidence (test set)")
    plt.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    # Postgres (warehouse)
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.environ["POSTGRES_USER"]
    pw = os.environ["POSTGRES_PASSWORD"]
    db = os.environ["POSTGRES_DB"]

    feature_table = os.getenv("FEATURE_TABLE", "features.iris_features")
    target_col = os.getenv("TARGET_COL", "target")

    # Split config
    test_size = float(os.getenv("TEST_SIZE", "0.2"))
    random_state = int(os.getenv("RANDOM_STATE", "42"))

    # Model config
    max_iter = int(os.getenv("MAX_ITER", "1000"))
    solver = os.getenv("SOLVER", "lbfgs")

    # MLflow
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "iris"))

    engine = create_engine(f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}")
    df = pd.read_sql(f"SELECT * FROM {feature_table}", engine)

    if target_col not in df.columns:
        raise ValueError(f"TARGET_COL='{target_col}' not in columns: {list(df.columns)}")

    # Build X/y
    X = df.drop(columns=[target_col, "row_id"], errors="ignore")
    y = df[target_col]

    # Basic sanity
    if X.shape[1] == 0:
        raise ValueError("No features left after dropping columns. Check your table.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    class_names = sorted(pd.unique(y))

    with mlflow.start_run():
        # params
        mlflow.log_param("feature_table", feature_table)
        mlflow.log_param("target_col", target_col)
        mlflow.log_param("dropped_cols", json.dumps([target_col, "row_id"]))
        mlflow.log_param("test_size", test_size)
        mlflow.log_param("random_state", random_state)
        mlflow.log_param("model", "LogisticRegression")
        mlflow.log_param("max_iter", max_iter)
        mlflow.log_param("solver", solver)
        mlflow.log_param("n_rows", int(df.shape[0]))
        mlflow.log_param("n_features", int(X.shape[1]))

        model = LogisticRegression(max_iter=max_iter, solver=solver)
        model.fit(X_train, y_train)

        # eval
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro")

        mlflow.log_metric("accuracy", float(acc))
        mlflow.log_metric("f1_macro", float(f1))
        mlflow.log_metric("n_train", int(len(X_train)))
        mlflow.log_metric("n_test", int(len(X_test)))

        # confusion matrix artifact
        cm = confusion_matrix(y_test, y_pred, labels=class_names)
        os.makedirs("/tmp/artifacts", exist_ok=True)
        cm_path = "/tmp/artifacts/confusion_matrix.png"
        save_confusion_matrix_png(cm, class_names, cm_path)
        mlflow.log_artifact(cm_path, artifact_path="eval")

        # classification report artifacts (txt + csv table)
        report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        report_txt = classification_report(y_test, y_pred, zero_division=0)

        report_txt_path = "/tmp/artifacts/classification_report.txt"
        with open(report_txt_path, "w") as f:
            f.write(report_txt)
        mlflow.log_artifact(report_txt_path, artifact_path="eval")

        # per-class table to csv (nice in MLflow UI to download)
        per_class_rows = []
        for cls in class_names:
            row = report_dict.get(str(cls), report_dict.get(cls, None))
            if row:
                per_class_rows.append({"class": cls, **row})
        per_class_df = pd.DataFrame(per_class_rows)
        per_class_csv_path = "/tmp/artifacts/per_class_metrics.csv"
        per_class_df.to_csv(per_class_csv_path, index=False)
        mlflow.log_artifact(per_class_csv_path, artifact_path="eval")

        # confidence histogram (only if predict_proba available)
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_test)
            y_proba_max = np.max(proba, axis=1)
            hist_path = "/tmp/artifacts/confidence_hist.png"
            save_confidence_histogram(y_proba_max, hist_path)
            mlflow.log_artifact(hist_path, artifact_path="eval")

        # log model
        mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        registered_model_name="IrisClassifier"
        )


if __name__ == "__main__":
    main()