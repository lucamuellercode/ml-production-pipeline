from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from pipeline import EvaluationResult


def _save_confusion_matrix_png(confusion_matrix_values, class_names, path: Path) -> None:
    fig = plt.figure()
    plt.imshow(confusion_matrix_values)
    plt.xticks(range(len(class_names)), class_names, rotation=45, ha="right")
    plt.yticks(range(len(class_names)), class_names)
    plt.xlabel("Predicted")
    plt.ylabel("True")

    for i in range(confusion_matrix_values.shape[0]):
        for j in range(confusion_matrix_values.shape[1]):
            plt.text(j, i, str(confusion_matrix_values[i, j]), ha="center", va="center")

    plt.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_confidence_histogram(y_proba_max, path: Path) -> None:
    fig = plt.figure()
    plt.hist(y_proba_max, bins=20)
    plt.xlabel("Top-1 predicted probability")
    plt.ylabel("Count")
    plt.title("Prediction confidence (test set)")
    plt.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_evaluation_artifacts(result: EvaluationResult, output_dir: str) -> dict[str, str]:
    artifacts_dir = Path(output_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    cm_path = artifacts_dir / "confusion_matrix.png"
    _save_confusion_matrix_png(result.confusion_matrix, result.class_names, cm_path)

    report_txt_path = artifacts_dir / "classification_report.txt"
    report_txt_path.write_text(result.classification_report_txt)

    per_class_rows = []
    for class_name in result.class_names:
        row = result.classification_report_dict.get(str(class_name))
        if row is None:
            row = result.classification_report_dict.get(class_name)
        if row:
            per_class_rows.append({"class": class_name, **row})

    per_class_df = pd.DataFrame(per_class_rows)
    per_class_csv_path = artifacts_dir / "per_class_metrics.csv"
    per_class_df.to_csv(per_class_csv_path, index=False)

    paths = {
        "confusion_matrix": str(cm_path),
        "classification_report": str(report_txt_path),
        "per_class_metrics": str(per_class_csv_path),
    }

    if result.y_proba_max is not None:
        hist_path = artifacts_dir / "confidence_hist.png"
        _save_confidence_histogram(result.y_proba_max, hist_path)
        paths["confidence_histogram"] = str(hist_path)

    return paths
