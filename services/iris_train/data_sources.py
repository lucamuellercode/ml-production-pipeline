import re

import pandas as pd
from sqlalchemy import create_engine, text

from config import PostgresConfig

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return identifier


def _safe_schema_table(schema_table: str) -> tuple[str, str]:
    parts = schema_table.split(".")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid feature table {schema_table!r}. Expected format '<schema>.<table>'."
        )
    return _safe_identifier(parts[0]), _safe_identifier(parts[1])


class PostgresFeatureSource:
    def __init__(self, pg_config: PostgresConfig, feature_table: str) -> None:
        self._pg_config = pg_config
        self._schema, self._table = _safe_schema_table(feature_table)

    def load(self) -> pd.DataFrame:
        engine = create_engine(self._pg_config.sqlalchemy_url)
        query = text(f'SELECT * FROM "{self._schema}"."{self._table}"')
        return pd.read_sql(query, engine)
