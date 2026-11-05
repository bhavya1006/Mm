"""Finds the references a complaint quotes and checks them against the connection register."""

import csv
import re
from pathlib import Path

import pandas as pd

from config import constants

ACCOUNT_NUMBER_PATTERN = re.compile(r"\bACC\d{8}\b")
METER_SERIAL_PATTERN = re.compile(r"\bMTR-[A-Z]{2}-\d{6}\b")
COMPLAINT_REFERENCE_PATTERN = re.compile(r"\bCMP\d{7}\b")

EXTRACTED_REFERENCE_FIELDS = (
    "message_id", "account_numbers", "meter_serials", "complaint_references",
    "unknown_accounts", "serials_on_another_account",
)


def _find_all(pattern, message):
    text = "" if message is None else str(message)
    found = pattern.findall(text)
    seen = []
    for one in found:
        if one not in seen:
            seen.append(one)
    return seen


def find_account_numbers(message):
    return _find_all(ACCOUNT_NUMBER_PATTERN, message)


def find_meter_serials(message):
    return _find_all(METER_SERIAL_PATTERN, message)


def find_complaint_references(message):
    return _find_all(COMPLAINT_REFERENCE_PATTERN, message)


def check_against_connection_register(accounts, serials, known_accounts, serial_owner):
    unknown_accounts = [one for one in accounts if one not in known_accounts]

    serials_on_another_account = []
    for serial in serials:
        owner = serial_owner.get(serial)
        if owner is not None and accounts and owner not in accounts:
            serials_on_another_account.append(serial)

    return {
        "unknown_accounts": unknown_accounts,
        "serials_on_another_account": serials_on_another_account,
    }


def extract_and_check(messages_path, register_path, extracted_path):
    messages = pd.read_csv(messages_path)
    register = pd.read_csv(register_path)

    known_accounts = set(register["account_number"])
    serial_owner = dict(zip(register["meter_serial"], register["account_number"]))

    extracted_path = Path(extracted_path)
    extracted_path.parent.mkdir(parents=True, exist_ok=True)

    faults = 0
    with open(extracted_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(EXTRACTED_REFERENCE_FIELDS)

        for _, row in messages.iterrows():
            text = row.get("message_text")
            accounts = find_account_numbers(text)
            serials = find_meter_serials(text)
            references = find_complaint_references(text)
            checked = check_against_connection_register(
                accounts, serials, known_accounts, serial_owner
            )
            faults += len(checked["unknown_accounts"]) + len(checked["serials_on_another_account"])

            writer.writerow((
                row["message_id"],
                ";".join(accounts),
                ";".join(serials),
                ";".join(references),
                ";".join(checked["unknown_accounts"]),
                ";".join(checked["serials_on_another_account"]),
            ))

    return {"messages": len(messages), "faults": faults}


if __name__ == "__main__":
    counted = extract_and_check(
        constants.COMPLAINT_MESSAGES_PATH, constants.CONNECTION_REGISTER_PATH,
        constants.EXTRACTED_REFERENCES_PATH,
    )
    print(counted)
