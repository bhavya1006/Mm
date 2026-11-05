"""The preparation every model of Weeks 3 to 5 is fitted through."""

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import pandas as pd

from config import constants

MODELLING_NUMBER_COLUMNS = (
    "sanctioned_load_kw",
    "cycle_days",
    "units_consumed",
    "twelve_month_average_units",
    "same_month_last_year_units",
    "consecutive_estimated_reads",
    "days_since_actual_read",
    "neighbourhood_average_units",
    "arrears_inr",
    "payment_defaults_last_year",
)

MODELLING_CATEGORY_COLUMNS = (
    "consumer_category",
    "division",
    "read_type",
    "seal_check_result",
    "meter_make",
)

MODELLING_COLUMNS = MODELLING_NUMBER_COLUMNS + MODELLING_CATEGORY_COLUMNS

EXCEPTION_COLUMN = "exception_class"

DERIVED_NUMBER_COLUMNS = ("consumption_ratio_to_average", "load_factor", "meter_age_years")
WIDENED_MODELLING_COLUMNS = MODELLING_COLUMNS + DERIVED_NUMBER_COLUMNS


def modelling_columns(widened=False):
    if widened:
        return WIDENED_MODELLING_COLUMNS
    return MODELLING_COLUMNS


def build_feature_pipeline(widened=False):
    number_columns = list(MODELLING_NUMBER_COLUMNS)
    if widened:
        number_columns += list(DERIVED_NUMBER_COLUMNS)

    numeric_pipeline = Pipeline([
        ("fill", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    category_pipeline = Pipeline([
        ("fill", SimpleImputer(strategy="most_frequent")),
        ("widen", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=0.01)),
    ])
    return ColumnTransformer([
        ("numbers", numeric_pipeline, number_columns),
        ("categories", category_pipeline, list(MODELLING_CATEGORY_COLUMNS)),
    ])


if __name__ == "__main__":
    book = pd.read_csv(constants.CLEAN_READING_BOOK_PATH).head(2000)
    prepared = build_feature_pipeline().fit_transform(book[list(MODELLING_COLUMNS)])
    numbers_out = prepared.shape[1] if not hasattr(prepared, "toarray") else prepared.shape[1]
    print(f"{len(MODELLING_COLUMNS)} columns in, {numbers_out} numbers out")
