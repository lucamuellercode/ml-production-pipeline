import pandas as pd

from schemas import IrisRecord

IRIS_FEATURE_COLUMNS = [
    "sepal_length_cm",
    "sepal_width_cm",
    "petal_length_cm",
    "petal_width_cm",
]


def build_features_frame(records: list[IrisRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [record.model_dump() for record in records],
        columns=IRIS_FEATURE_COLUMNS,
    )
