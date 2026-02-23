from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from config import ModelConfig, SplitConfig


@dataclass(frozen=True)
class SplitData:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


@dataclass(frozen=True)
class EvaluationResult:
    accuracy: float
    f1_macro: float
    confusion_matrix: np.ndarray
    classification_report_txt: str
    classification_report_dict: dict
    y_proba_max: np.ndarray | None
    class_names: list


def prepare_features(df: pd.DataFrame, target_column: str, drop_columns: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    if target_column not in df.columns:
        raise ValueError(f"TARGET_COL='{target_column}' not in columns: {list(df.columns)}")

    drop_candidates = [target_column, *drop_columns]
    X = df.drop(columns=drop_candidates, errors="ignore")
    y = df[target_column]

    if X.shape[1] == 0:
        raise ValueError("No features left after dropping columns. Check FEATURE_TABLE/TARGET_COL/DROP_COLUMNS.")

    return X, y


def split_dataset(X: pd.DataFrame, y: pd.Series, split_cfg: SplitConfig) -> SplitData:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=split_cfg.test_size,
        random_state=split_cfg.random_state,
        stratify=y,
    )
    return SplitData(X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test)


def train_model(split_data: SplitData, model_cfg: ModelConfig) -> LogisticRegression:
    model = LogisticRegression(max_iter=model_cfg.max_iter, solver=model_cfg.solver)
    model.fit(split_data.X_train, split_data.y_train)
    return model


def evaluate_model(model: LogisticRegression, split_data: SplitData) -> EvaluationResult:
    y_pred = model.predict(split_data.X_test)
    class_names = sorted(pd.unique(split_data.y_test))

    y_proba_max = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(split_data.X_test)
        y_proba_max = np.max(proba, axis=1)

    return EvaluationResult(
        accuracy=float(accuracy_score(split_data.y_test, y_pred)),
        f1_macro=float(f1_score(split_data.y_test, y_pred, average="macro")),
        confusion_matrix=confusion_matrix(split_data.y_test, y_pred, labels=class_names),
        classification_report_txt=classification_report(
            split_data.y_test, y_pred, zero_division=0
        ),
        classification_report_dict=classification_report(
            split_data.y_test, y_pred, output_dict=True, zero_division=0
        ),
        y_proba_max=y_proba_max,
        class_names=class_names,
    )
