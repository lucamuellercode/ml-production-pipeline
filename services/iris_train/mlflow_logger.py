import json

import mlflow
import mlflow.sklearn

from config import MlflowConfig
from pipeline import EvaluationResult, SplitData


def configure_mlflow(mlflow_cfg: MlflowConfig) -> None:
    mlflow.set_tracking_uri(mlflow_cfg.tracking_uri)
    mlflow.set_experiment(mlflow_cfg.experiment)


def log_training_run(
    *,
    mlflow_cfg: MlflowConfig,
    model,
    feature_table: str,
    target_col: str,
    dropped_cols: list[str],
    n_rows: int,
    n_features: int,
    max_iter: int,
    solver: str,
    split_test_size: float,
    split_random_state: int,
    split_data: SplitData,
    evaluation: EvaluationResult,
    artifact_paths: dict[str, str],
) -> None:
    with mlflow.start_run():
        mlflow.log_param("feature_table", feature_table)
        mlflow.log_param("target_col", target_col)
        mlflow.log_param("dropped_cols", json.dumps(dropped_cols))
        mlflow.log_param("test_size", split_test_size)
        mlflow.log_param("random_state", split_random_state)
        mlflow.log_param("model", "LogisticRegression")
        mlflow.log_param("max_iter", max_iter)
        mlflow.log_param("solver", solver)
        mlflow.log_param("n_rows", int(n_rows))
        mlflow.log_param("n_features", int(n_features))

        mlflow.log_metric("accuracy", evaluation.accuracy)
        mlflow.log_metric("f1_macro", evaluation.f1_macro)
        mlflow.log_metric("n_train", int(len(split_data.X_train)))
        mlflow.log_metric("n_test", int(len(split_data.X_test)))

        mlflow.log_artifact(artifact_paths["confusion_matrix"], artifact_path="eval")
        mlflow.log_artifact(artifact_paths["classification_report"], artifact_path="eval")
        mlflow.log_artifact(artifact_paths["per_class_metrics"], artifact_path="eval")

        if "confidence_histogram" in artifact_paths:
            mlflow.log_artifact(artifact_paths["confidence_histogram"], artifact_path="eval")

        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=mlflow_cfg.registered_model_name,
        )
