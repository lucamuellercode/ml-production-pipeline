from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd

from settings import IrisApiSettings


class DummyIrisModel:
    def predict(self, features_df: pd.DataFrame) -> list[int]:
        return [0 for _ in range(len(features_df))]


@dataclass
class LoadedModel:
    backend: Literal["dummy", "mlflow"]
    model_uri: str | None
    model: Any


def load_model(settings: IrisApiSettings) -> LoadedModel:
    if settings.model_uri is None:
        return LoadedModel(
            backend="dummy",
            model_uri=None,
            model=DummyIrisModel(),
        )

    try:
        import mlflow
    except ImportError as exc:
        raise RuntimeError(
            "MODEL_URI is set, but mlflow is not installed in this environment."
        ) from exc

    if settings.mlflow_tracking_uri:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    model = mlflow.pyfunc.load_model(settings.model_uri)
    return LoadedModel(
        backend="mlflow",
        model_uri=settings.model_uri,
        model=model,
    )


def run_prediction(loaded_model: LoadedModel, features_df: pd.DataFrame) -> list[int | float | str]:
    raw_predictions = loaded_model.model.predict(features_df)

    if hasattr(raw_predictions, "tolist"):
        raw_predictions = raw_predictions.tolist()

    normalized: list[int | float | str] = []
    for value in raw_predictions:
        if hasattr(value, "item"):
            value = value.item()
        normalized.append(value)
    return normalized
