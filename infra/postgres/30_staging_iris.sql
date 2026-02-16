CREATE TABLE IF NOT EXISTS staging.iris_clean (
  sepal_length_cm  DOUBLE PRECISION NOT NULL,
  sepal_width_cm   DOUBLE PRECISION NOT NULL,
  petal_length_cm  DOUBLE PRECISION NOT NULL,
  petal_width_cm   DOUBLE PRECISION NOT NULL,
  target           INTEGER NOT NULL
);
