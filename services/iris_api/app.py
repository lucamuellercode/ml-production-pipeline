"""Iris demo API with startup model selection via MODEL_URI."""

from fastapi import HTTPException
from fastapi import FastAPI

from model_loader import LoadedModel, load_model, run_prediction
from predictor import IRIS_FEATURE_COLUMNS, build_features_frame
from schemas import ModelInfoResponse, PredictRequest, PredictResponse
from settings import load_settings


app = FastAPI(title="Iris Demo API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    settings = load_settings()
    loaded_model = load_model(settings)
    app.state.loaded_model = loaded_model


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Iris demo API. Use /health, /model-info and /predict."}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info() -> ModelInfoResponse:
    loaded_model: LoadedModel = app.state.loaded_model
    return ModelInfoResponse(
        model_backend=loaded_model.backend,
        model_loaded=True,
        model_uri=loaded_model.model_uri,
        feature_columns=IRIS_FEATURE_COLUMNS,
        note=(
            "Dummy predictor currently returns class 0 for every record."
            if loaded_model.backend == "dummy"
            else "Model is loaded from MLflow using MODEL_URI."
        ),
    )


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    loaded_model: LoadedModel = app.state.loaded_model
    features_df = build_features_frame(payload.records)

    try:
        predictions = run_prediction(loaded_model, features_df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc
    return PredictResponse(predictions=predictions)
