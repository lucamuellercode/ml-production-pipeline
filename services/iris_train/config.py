import os
from dataclasses import dataclass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class DataConfig:
    feature_table: str
    target_column: str
    drop_columns: list[str]


@dataclass(frozen=True)
class SplitConfig:
    test_size: float
    random_state: int


@dataclass(frozen=True)
class ModelConfig:
    max_iter: int
    solver: str


@dataclass(frozen=True)
class MlflowConfig:
    tracking_uri: str
    experiment: str
    registered_model_name: str


@dataclass(frozen=True)
class ArtifactConfig:
    output_dir: str


@dataclass(frozen=True)
class TrainingAppConfig:
    postgres: PostgresConfig
    data: DataConfig
    split: SplitConfig
    model: ModelConfig
    mlflow: MlflowConfig
    artifacts: ArtifactConfig

    @classmethod
    def from_env(cls) -> "TrainingAppConfig":
        return cls(
            postgres=PostgresConfig(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=_required_env("POSTGRES_USER"),
                password=_required_env("POSTGRES_PASSWORD"),
                database=_required_env("POSTGRES_DB"),
            ),
            data=DataConfig(
                feature_table=os.getenv("FEATURE_TABLE", "features.iris_features"),
                target_column=os.getenv("TARGET_COL", "target"),
                drop_columns=_parse_csv_env("DROP_COLUMNS", "row_id"),
            ),
            split=SplitConfig(
                test_size=float(os.getenv("TEST_SIZE", "0.2")),
                random_state=int(os.getenv("RANDOM_STATE", "42")),
            ),
            model=ModelConfig(
                max_iter=int(os.getenv("MAX_ITER", "1000")),
                solver=os.getenv("SOLVER", "lbfgs"),
            ),
            mlflow=MlflowConfig(
                tracking_uri=_required_env("MLFLOW_TRACKING_URI"),
                experiment=os.getenv("MLFLOW_EXPERIMENT", "iris"),
                registered_model_name=os.getenv("REGISTERED_MODEL_NAME", "IrisClassifier"),
            ),
            artifacts=ArtifactConfig(
                output_dir=os.getenv("ARTIFACT_DIR", "/tmp/artifacts"),
            ),
        )
