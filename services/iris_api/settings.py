import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IrisApiSettings:
    mlflow_tracking_uri: str | None
    model_uri: str | None


def _normalize_optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def load_settings() -> IrisApiSettings:
    return IrisApiSettings(
        mlflow_tracking_uri=_normalize_optional_env("MLFLOW_TRACKING_URI"),
        model_uri=_normalize_optional_env("MODEL_URI"),
    )
