"""Three derived columns, added without altering what they were derived from."""

from pathlib import Path

import pandas as pd

from config import constants
from metermind.exception_models.feature_pipeline import modelling_columns

DAYS_IN_A_YEAR = 365.25


def add_consumption_ratio_to_average(book):
    widened = book.copy()
    average = widened["twelve_month_average_units"]
    ratio = widened["units_consumed"] / average
    ratio = ratio.where(average != 0, 1.0)
    widened["consumption_ratio_to_average"] = ratio
    return widened


def add_load_factor(book):
    widened = book.copy()
    drawable = widened["sanctioned_load_kw"] * constants.HOURS_IN_A_DAY * widened["cycle_days"]
    widened["load_factor"] = widened["units_consumed"] / drawable
    return widened


def add_meter_age_years(book):
    widened = book.copy()
    installed_on = pd.to_datetime(widened["meter_install_date"], errors="coerce")
    cycle_ended_on = pd.to_datetime(widened["cycle_end_date"], errors="coerce")
    age_days = (cycle_ended_on - installed_on).dt.days
    widened["meter_age_years"] = age_days / DAYS_IN_A_YEAR
    return widened


def widen_readings(book):
    widened = add_consumption_ratio_to_average(book)
    widened = add_load_factor(widened)
    widened = add_meter_age_years(widened)
    return widened


def measure_feature_lift(book):
    from metermind.exception_models.baseline_model import build_baseline_model, split_readings

    narrow_fitting, narrow_held_out, fitting_classes, held_out_classes = split_readings(
        book, modelling_columns(False)
    )
    widened_book = widen_readings(book)
    widened_fitting, widened_held_out, _, _ = split_readings(
        widened_book, modelling_columns(True)
    )

    narrow_model = build_baseline_model(widened=False)
    narrow_model.fit(narrow_fitting, fitting_classes)
    narrow_score = narrow_model.score(narrow_held_out, held_out_classes)

    widened_model = build_baseline_model(widened=True)
    widened_model.fit(widened_fitting, fitting_classes)
    widened_score = widened_model.score(widened_held_out, held_out_classes)

    narrow_rounded = round(narrow_score, constants.MEASUREMENT_DECIMAL_PLACES)
    widened_rounded = round(widened_score, constants.MEASUREMENT_DECIMAL_PLACES)
    lift_rounded = round(widened_rounded - narrow_rounded, constants.MEASUREMENT_DECIMAL_PLACES)

    return {"narrow": narrow_rounded, "widened": widened_rounded, "lift": lift_rounded}


if __name__ == "__main__":
    import json

    book = pd.read_csv(constants.CLEAN_READING_BOOK_PATH)
    widened = widen_readings(book)

    Path(constants.WIDENED_READINGS_PATH).parent.mkdir(parents=True, exist_ok=True)
    widened.to_csv(constants.WIDENED_READINGS_PATH, index=False)

    lift = measure_feature_lift(book.sample(min(2000, len(book)), random_state=constants.MODEL_SEED))
    Path(constants.FEATURE_LIFT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(constants.FEATURE_LIFT_PATH).write_text(json.dumps(lift, indent=2))

    print(f"narrow   {lift['narrow']}")
    print(f"widened  {lift['widened']}")
    print(f"lift     {lift['lift']}")
