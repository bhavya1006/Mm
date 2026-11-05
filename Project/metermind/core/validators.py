"""Format checks every layer of the platform validates through."""

import re

from config import constants

_ACCOUNT_NUMBER_PATTERN = re.compile(constants.ACCOUNT_NUMBER_PATTERN)
_METER_SERIAL_PATTERN = re.compile(constants.METER_SERIAL_PATTERN)
_BILLING_PERIOD_PATTERN = re.compile(constants.BILLING_PERIOD_PATTERN)
_EMAIL_ADDRESS_PATTERN = re.compile(constants.EMAIL_ADDRESS_PATTERN)


def validate_account_number(account_number):
    if not isinstance(account_number, str):
        return False
    return bool(_ACCOUNT_NUMBER_PATTERN.fullmatch(account_number.strip()))


def validate_meter_serial(meter_serial):
    if not isinstance(meter_serial, str):
        return False
    return bool(_METER_SERIAL_PATTERN.fullmatch(meter_serial.strip()))


def validate_billing_period(billing_period):
    if not isinstance(billing_period, str):
        return False
    return bool(_BILLING_PERIOD_PATTERN.fullmatch(billing_period.strip()))


def validate_email_address(email_address):
    if not isinstance(email_address, str):
        return False
    return bool(_EMAIL_ADDRESS_PATTERN.fullmatch(email_address.strip().lower()))


if __name__ == "__main__":
    print(f"account number ACC10000123    well formed: {validate_account_number('ACC10000123')}")
    print(f"account number ACC1           well formed: {validate_account_number('ACC1')}")
    print(f"billing period 2026-06        well formed: {validate_billing_period('2026-06')}")
    print(f"billing period 2026-13        well formed: {validate_billing_period('2026-13')}")
