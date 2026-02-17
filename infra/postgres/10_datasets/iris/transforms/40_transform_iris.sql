TRUNCATE staging.iris_clean;

INSERT INTO staging.iris_clean (
  sepal_length_cm,
  sepal_width_cm,
  petal_length_cm,
  petal_width_cm,
  target
)
SELECT
  "sepal length (cm)",
  "sepal width (cm)",
  "petal length (cm)",
  "petal width (cm)",
  target
FROM raw.iris;
