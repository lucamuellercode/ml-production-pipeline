CREATE TABLE IF NOT EXISTS features.iris_features (
  row_id BIGSERIAL PRIMARY KEY,
  sepal_length_cm DOUBLE PRECISION NOT NULL,
  sepal_width_cm DOUBLE PRECISION NOT NULL,
  petal_length_cm DOUBLE PRECISION NOT NULL,
  petal_width_cm DOUBLE PRECISION NOT NULL,
  target INT NOT NULL
);
