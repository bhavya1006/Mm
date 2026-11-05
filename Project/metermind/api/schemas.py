"""The models every route validates against."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from config import constants
from metermind.core import validators
from metermind.data_access.cleaning_pipeline import READ_DATE_FORMATS


class HealthReply(BaseModel):
    service: str
    status: str


class ReadingSubmission(BaseModel):
    account_number: str
    meter_serial: str
    consumer_category: str
    billing_period: str
    sanctioned_load_kw: float = Field(gt=0, le=500)
    cycle_days: int = Field(ge=constants.MINIMUM_CYCLE_DAYS, le=constants.MAXIMUM_CYCLE_DAYS)
    previous_reading: float = Field(ge=0, lt=constants.METER_ROLLOVER_UNITS)
    current_reading: float = Field(ge=0, lt=constants.METER_ROLLOVER_UNITS)
    read_type: str = "actual"
    read_date: Optional[str] = None

    @field_validator("account_number")
    @classmethod
    def account_number_is_well_formed(cls, given):
        if not validators.validate_account_number(given):
            raise ValueError("account_number must look like ACC10000000")
        return given.strip().upper()

    @field_validator("meter_serial")
    @classmethod
    def meter_serial_is_well_formed(cls, given):
        if not validators.validate_meter_serial(given):
            raise ValueError("meter_serial must look like MTR-AB-123456")
        return given

    @field_validator("billing_period")
    @classmethod
    def billing_period_is_well_formed(cls, given):
        if not validators.validate_billing_period(given):
            raise ValueError("billing_period must look like 2026-06")
        return given

    @field_validator("consumer_category")
    @classmethod
    def spelling_is_settled_at_the_door(cls, given):
        settled = given.strip().lower()
        return constants.CONSUMER_CATEGORY_CORRECTIONS.get(settled, settled)

    @field_validator("read_date")
    @classmethod
    def date_is_readable(cls, given):
        if given is None:
            return given
        stripped = given.strip()
        for date_format in READ_DATE_FORMATS:
            try:
                from datetime import datetime
                return datetime.strptime(stripped, date_format).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError("read_date must be in one of the shapes the field application writes")


class ReadingReply(BaseModel):
    reading_id: str
    account_number: str
    consumer_category: str
    units_consumed: float
    energy_charge_inr: float
    fixed_charge_inr: float
    net_bill_inr: float
    is_billable: bool
    refusal_reasons: list[str]


class CaseStatusRequest(BaseModel):
    wanted_status: str
    noted_by: str


class CaseStatusReply(BaseModel):
    reading_id: str
    from_status: str
    to_status: str
    recorded_by: str


class PagedReadings(BaseModel):
    readings: list[ReadingReply]
    page: int
    page_size: int
    total: int


class ScreeningRequest(ReadingSubmission):
    units_consumed: float
    twelve_month_average_units: float
    same_month_last_year_units: float
    consecutive_estimated_reads: int
    days_since_actual_read: int
    neighbourhood_average_units: float
    arrears_inr: float
    payment_defaults_last_year: int
    seal_check_result: str
    meter_make: str
    division: str
    meter_install_date: str
    cycle_end_date: str


class ScreeningReply(BaseModel):
    account_number: str
    billing_period: str
    exception_class: str
    confidence: float
    goes_to: str

