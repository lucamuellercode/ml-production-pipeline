CREATE TABLE IF NOT EXISTS features.iris_features (
    row_id BIGSERIAL PRIMARY KEY,
    sepal_length_cm DOUBLE PRECISION NOT NULL,
    sepal_width_cm DOUBLE PRECISION NOT NULL,
    petal_length_cm DOUBLE PRECISION NOT NULL,
    petal_width_cm DOUBLE PRECISION NOT NULL,
    target INT NOT NULL
);

TRUNCATE TABLE features.iris_features;

INSERT INTO features.iris_features (
    sepal_length_cm,
    sepal_width_cm,
    petal_length_cm,
    petal_width_cm,
    target
)
SELECT
    sepal_length_cm,
    sepal_width_cm,
    petal_length_cm,
    petal_width_cm,
    target

FROM staging.iris_clean;