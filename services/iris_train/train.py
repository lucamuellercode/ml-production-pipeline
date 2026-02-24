import logging

from artifacts import write_evaluation_artifacts
from config import TrainingAppConfig
from data_sources import PostgresFeatureSource
from mlflow_logger import configure_mlflow, log_training_run
from pipeline import evaluate_model, prepare_features, split_dataset, train_model


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )


def main() -> None:
    _setup_logging()
    logger = logging.getLogger("iris_train")

    cfg = TrainingAppConfig.from_env()
    configure_mlflow(cfg.mlflow)
    logger.info(
        "Config loaded for dataset=%s version=%s experiment=%s",
        cfg.data.dataset_name,
        cfg.data.dataset_version,
        cfg.mlflow.experiment,
    )

    logger.info("Loading features from table: %s", cfg.data.feature_table)
    feature_source = PostgresFeatureSource(cfg.postgres, cfg.data.feature_table)
    df = feature_source.load()

    X, y = prepare_features(
        df,
        target_column=cfg.data.target_column,
        drop_columns=cfg.data.drop_columns,
    )
    split_data = split_dataset(X, y, cfg.split)

    logger.info(
        "Training model with %s rows (%s train / %s test)",
        len(df),
        len(split_data.X_train),
        len(split_data.X_test),
    )
    model = train_model(split_data, cfg.model)
    evaluation = evaluate_model(model, split_data)

    artifact_paths = write_evaluation_artifacts(evaluation, cfg.artifacts.output_dir)

    log_training_run(
        mlflow_cfg=cfg.mlflow,
        model=model,
        dataset_name=cfg.data.dataset_name,
        dataset_version=cfg.data.dataset_version,
        feature_table=cfg.data.feature_table,
        target_col=cfg.data.target_column,
        dropped_cols=[cfg.data.target_column, *cfg.data.drop_columns],
        n_rows=df.shape[0],
        n_features=X.shape[1],
        max_iter=cfg.model.max_iter,
        solver=cfg.model.solver,
        split_test_size=cfg.split.test_size,
        split_random_state=cfg.split.random_state,
        split_data=split_data,
        evaluation=evaluation,
        artifact_paths=artifact_paths,
    )

    logger.info(
        "Training complete. accuracy=%.4f f1_macro=%.4f",
        evaluation.accuracy,
        evaluation.f1_macro,
    )


if __name__ == "__main__":
    main()
