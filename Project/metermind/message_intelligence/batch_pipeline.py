"""Runs a whole corpus without one bad message stopping it."""

import csv
from pathlib import Path

from config import constants

BATCH_FAILURE_FIELDS = ("message_id", "reason")


class MessageFailure(Exception):
    def __init__(self, message_id, reason):
        super().__init__(f"{message_id}: {reason}")
        self.message_id = message_id
        self.reason = reason


def run_batch(messages, handle_one, failures_path=constants.BATCH_FAILURES_PATH):
    results = []
    failures = []

    for message in messages:
        message_id = message.get("message_id") if isinstance(message, dict) \
            else getattr(message, "message_id", None)
        try:
            results.append(handle_one(message))
        except Exception as failed:
            failure = MessageFailure(message_id, str(failed))
            results.append(failure)
            failures.append(failure)

    failures_path = Path(failures_path)
    failures_path.parent.mkdir(parents=True, exist_ok=True)
    with open(failures_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(BATCH_FAILURE_FIELDS)
        for one in failures:
            writer.writerow((one.message_id, one.reason))

    return results


if __name__ == "__main__":
    def double_it(message):
        return message["value"] * 2

    handled = run_batch(
        [{"message_id": "MSG000001", "value": 5}, {"message_id": "MSG000002"}],
        double_it,
    )
    print(f"handled and returned: {len(handled)}")
    for one in handled:
        if isinstance(one, MessageFailure):
            print(f"{one.message_id} failed, and the batch carried on: {one.reason!r}")
    print(f"what failed is written to: {constants.BATCH_FAILURES_PATH}")
