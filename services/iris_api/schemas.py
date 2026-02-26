from typing import Literal

from pydantic import BaseModel, Field


class IrisRecord(BaseModel):
    sepal_length_cm: float = Field(..., gt=0)
    sepal_width_cm: float = Field(..., gt=0)
    petal_length_cm: float = Field(..., gt=0)
    petal_width_cm: float = Field(..., gt=0)


class PredictRequest(BaseModel):
    records: list[IrisRecord] = Field(..., min_length=1)


class PredictResponse(BaseModel):
    predictions: list[int | float | str]


class ModelInfoResponse(BaseModel):
    model_backend: Literal["dummy", "mlflow"]
    model_loaded: bool
    model_uri: str | None = None
    feature_columns: list[str]
    note: str
