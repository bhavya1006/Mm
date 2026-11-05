"""Cleans the raw reading book into the file every model trusts."""

from pathlib import Path

import pandas as pd

from config import constants
from metermind.core.validators import validate_billing_period

REJECTION_REASONS = (
    "a required field is empty",
    "the read date could not be read",
    "the billing period is not a year and a month",
    "the consumer category has no tariff schedule",
    "the sanctioned load is not above zero",
    "the billing cycle length is outside the permitted range",
    "the current reading is below the previous reading",
    "the consumption could not be drawn by any load on file",
)

REQUIRED_FIELDS = (
    "reading_id",
    "account_number",
    "consumer_category",
    "sanctioned_load_kw",
    "billing_period",
    "cycle_days",
    "previous_reading",
    "current_reading",
    "units_consumed",
)

READ_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%d.%m.%Y")

_NUMERIC_COLUMNS = (
    "sanctioned_load_kw",
    "cycle_days",
    "previous_reading",
    "current_reading",
    "units_consumed",
)


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def parse_read_dates(book):
    read_on = pd.Series(pd.NaT, index=book.index, dtype="datetime64[ns]")
    remaining = read_on.isna()
    for date_format in READ_DATE_FORMATS:
        if not remaining.any():
            break
        parsed = pd.to_datetime(
            book.loc[remaining, "read_date"], format=date_format, errors="coerce"
        )
        read_on.loc[remaining] = parsed
        remaining = read_on.isna()
    return read_on


def first_broken_rule(row):
    for field in REQUIRED_FIELDS:
        if _is_missing(row.get(field)):
            return REJECTION_REASONS[0]

    if pd.isna(row.get("read_on")):
        return REJECTION_REASONS[1]

    if not validate_billing_period(str(row["billing_period"]).strip()):
        return REJECTION_REASONS[2]

    if str(row["consumer_category"]).strip().lower() not in constants.CONSUMER_CATEGORIES:
        return REJECTION_REASONS[3]

    if not (row["sanctioned_load_kw"] > 0):
        return REJECTION_REASONS[4]

    if not (constants.MINIMUM_CYCLE_DAYS <= row["cycle_days"] <= constants.MAXIMUM_CYCLE_DAYS):
        return REJECTION_REASONS[5]

    physical_maximum_units = (
        row["sanctioned_load_kw"] * constants.HOURS_IN_A_DAY * row["cycle_days"]
        * constants.IMPLAUSIBLE_CAPACITY_FACTOR
    )

    if row["current_reading"] < row["previous_reading"]:
        would_have_reached_ceiling = (
            row["previous_reading"] + physical_maximum_units >= constants.METER_ROLLOVER_UNITS
        )
        if not would_have_reached_ceiling:
            return REJECTION_REASONS[6]

    if row["units_consumed"] > physical_maximum_units:
        return REJECTION_REASONS[7]

    return ""


def clean_reading_book(book_path, clean_path, rejected_path):
    book = pd.read_csv(book_path)

    for column in _NUMERIC_COLUMNS:
        if column in book.columns:
            book[column] = pd.to_numeric(book[column], errors="coerce")

    book["read_on"] = parse_read_dates(book)
    reasons = book.apply(first_broken_rule, axis=1)

    clean_path, rejected_path = Path(clean_path), Path(rejected_path)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)

    is_rejected = reasons != ""

    rejected = book.loc[is_rejected].drop(columns=["read_on"]).copy()
    rejected["rejection_reason"] = reasons.loc[is_rejected]
    rejected.to_csv(rejected_path, index=False)

    clean = book.loc[~is_rejected].drop(columns=["read_on"]).copy()
    clean.to_csv(clean_path, index=False)

    return {"kept": len(clean), "rejected": len(rejected)}


if __name__ == "__main__":
    from metermind.core.tariff_calculations import calculate_bill_amount

    print("units consumed:", 467.0)
    print("energy charge :", round(calculate_bill_amount("domestic", 467.0, 3.0), 2))
    counted = clean_reading_book(
        constants.READING_BOOK_TRAIN_PATH,
        constants.CLEAN_READING_BOOK_PATH,
        constants.REJECTED_READING_BOOK_PATH,
    )
    print(f"kept: {counted['kept']} rejected: {counted['rejected']}")
