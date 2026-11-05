"""Four tools, each doing exactly what a billing office does by hand."""

import json
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from config import constants
from metermind.core.exceptions import ToolError
from metermind.core.validators import validate_billing_period

readings_database_path = constants.READINGS_DATABASE_PATH
champion_model_path = constants.CHAMPION_MODEL_PATH
operating_rule_path = constants.OPERATING_RULE_PATH
exception_report_path = constants.EXCEPTION_REPORT_PATH
tariff_store_directory = constants.TARIFF_STORE_DIRECTORY

opened_resources = {}


def _database():
    if "database" not in opened_resources:
        from metermind.data_access.database_loader import ReadingDatabase
        opened_resources["database"] = ReadingDatabase(readings_database_path)
    return opened_resources["database"]


def _reading_or_fail(reading_identifier):
    row = _database().find_reading_by_identifier(reading_identifier)
    if row is None:
        raise ToolError(f"there is no reading {reading_identifier}")
    return row


class LookUpReadingArgs(BaseModel):
    reading_identifier: str


class CalculateBillArgs(BaseModel):
    consumer_category: str
    units_consumed: float = Field(ge=0)
    sanctioned_load_kw: float = Field(gt=0)

    @field_validator("consumer_category")
    @classmethod
    def category_is_known(cls, given):
        if given not in constants.CONSUMER_CATEGORIES:
            raise ValueError(f"{given} has no published tariff schedule")
        return given


class PredictReadingExceptionArgs(BaseModel):
    reading_identifier: str


class SearchTariffOrderArgs(BaseModel):
    question: str
    consumer_category: str
    billing_period: str

    @field_validator("consumer_category")
    @classmethod
    def category_is_known(cls, given):
        if given not in constants.CONSUMER_CATEGORIES:
            raise ValueError(f"{given} has no published tariff schedule")
        return given

    @field_validator("billing_period")
    @classmethod
    def billing_period_is_well_formed(cls, given):
        if not validate_billing_period(given):
            raise ValueError("billing_period must look like 2026-06")
        return given


@tool("look_up_reading", args_schema=LookUpReadingArgs)
def look_up_reading(reading_identifier: str) -> dict:
    """Look up a stored meter reading by its identifier and return its stored fields. Use this
    when a question is about a specific reading that has already been submitted or billed, and
    you have (or the consumer has given you) its reading_id, such as RDG20000123."""
    return _reading_or_fail(reading_identifier)


@tool("calculate_bill", args_schema=CalculateBillArgs)
def calculate_bill(consumer_category: str, units_consumed: float,
                    sanctioned_load_kw: float) -> dict:
    """Calculate what a cycle would cost under the published tariff schedule, given its consumer
    category, units consumed and sanctioned load in kilowatts. Use this to answer "how much
    would this cost" or to check the arithmetic behind a bill someone is disputing."""
    from metermind.core.tariff_calculations import calculate_bill_amount

    amount = calculate_bill_amount(consumer_category, units_consumed, sanctioned_load_kw)
    return {"current_demand_inr": round(amount, constants.CURRENCY_DECIMAL_PLACES)}


@tool("predict_reading_exception", args_schema=PredictReadingExceptionArgs)
def predict_reading_exception(reading_identifier: str) -> dict:
    """Read a stored reading and run it through the champion exception model under its operating
    rule, returning the class it was decided as and how precise that class has historically been
    for the model. Use this to explain why a reading was flagged or what is suspected wrong with
    a meter or bill."""
    import pandas as pd

    from metermind.exception_models.champion_model import predict_with_rule
    from metermind.exception_models.feature_engineering import widen_readings
    from metermind.exception_models.feature_pipeline import MODELLING_NUMBER_COLUMNS, modelling_columns

    row = _reading_or_fail(reading_identifier)

    if "champion" not in opened_resources:
        from metermind.exception_models.baseline_model import load_model
        opened_resources["champion"] = load_model(champion_model_path)
    champion = opened_resources["champion"]

    if "rule" not in opened_resources:
        opened_resources["rule"] = json.loads(Path(operating_rule_path).read_text())
    rule = opened_resources["rule"]

    row_frame = pd.DataFrame([row])
    for column in MODELLING_NUMBER_COLUMNS:
        if column in row_frame.columns:
            row_frame[column] = pd.to_numeric(row_frame[column], errors="coerce")

    widened = widen_readings(row_frame)
    columns = list(modelling_columns(True))
    decided = predict_with_rule(champion, widened[columns], rule["tamper_floor"], rule["fault_floor"])
    exception_class = decided[0]

    if "report" not in opened_resources:
        opened_resources["report"] = pd.read_csv(exception_report_path).set_index("exception_class")
    report = opened_resources["report"]
    precision = float(report.loc[exception_class, "precision"]) if exception_class in report.index else None

    return {"exception_class": exception_class, "precision": precision}


@tool("search_tariff_order", args_schema=SearchTariffOrderArgs)
def search_tariff_order(question: str, consumer_category: str, billing_period: str) -> list:
    """Search the published tariff orders for the schedule that answers a rate, charge or rule
    question, filtered to the one order that was actually in force for the given consumer
    category and billing period. Use this to answer questions about rates, fixed charges, duty,
    rebates or billing rules from the published tariff."""
    from metermind.retrieval.filtered_search import filtered_search

    if "embedder" not in opened_resources:
        from metermind.retrieval.vector_store import load_embedder
        opened_resources["embedder"] = load_embedder()
    embedder = opened_resources["embedder"]

    if "collection" not in opened_resources:
        from metermind.retrieval.vector_store import open_tariff_store
        opened_resources["collection"] = open_tariff_store(tariff_store_directory)
    collection = opened_resources["collection"]

    if "manifest" not in opened_resources:
        from metermind.retrieval.document_loader import read_manifest
        opened_resources["manifest"] = read_manifest()
    manifest = opened_resources["manifest"]

    return filtered_search(collection, question, embedder, consumer_category, billing_period, manifest)


READING_TOOLS = [look_up_reading, calculate_bill, predict_reading_exception, search_tariff_order]
