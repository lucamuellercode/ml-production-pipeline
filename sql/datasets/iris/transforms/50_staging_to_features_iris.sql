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
