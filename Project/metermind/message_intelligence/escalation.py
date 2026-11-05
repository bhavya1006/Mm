"""Complaints escalate on the published number of signals, never on one alone."""

import csv
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from config import constants
from metermind.message_intelligence.batch_pipeline import MessageFailure, run_batch

TONE_PROMPT = (
    "Read the tone of this consumer complaint about an electricity connection and answer with "
    "only the tone and the evidence for it. The tone must be exactly one of: calm, frustrated, "
    "angry.\n\n"
    "Complaint: {message_text}\n\n"
    "Reply with a JSON object and nothing else, holding two keys: \"tone\" (one of the three "
    "words above) and \"reason\" (a short phrase quoted from the complaint that shows it)."
)

ESCALATION_FIELDS = ("message_id", "age_days", "urgency", "tone", "escalate", "signals")


def complaint_age_days(received_date, today=None):
    received_on = datetime.strptime(str(received_date).strip(), "%Y-%m-%d").date()
    as_of = today if today is not None else date.today()
    return (as_of - received_on).days


def decide_escalation(age_days, urgency, tone):
    signals = []
    if age_days > constants.COMPLAINT_AGE_ESCALATION_DAYS:
        signals.append("waiting too long")
    if urgency in constants.ESCALATING_URGENCIES:
        signals.append("urgency")
    if tone in constants.ESCALATING_TONES:
        signals.append("tone")

    escalate = len(signals) >= constants.ESCALATION_SIGNALS_NEEDED
    return {"escalate": escalate, "signals": signals}


def read_tone(message_text, cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    from metermind.message_intelligence.llm_client import (
        LanguageModelError,
        ask_model,
        read_answer,
    )

    prompt = TONE_PROMPT.format(message_text=message_text)
    answered = ask_model(prompt, cache_path)
    read = read_answer(answered, constants.TONE_REPLY_KEYS)

    tone = read["tone"]
    if tone not in constants.TONE_READINGS:
        raise LanguageModelError(f"{tone!r} is not a tone this platform reads")

    return {"tone": tone, "reason": read["reason"]}


def escalate_one_message(message, urgency_model, today=None,
                          cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    age_days = complaint_age_days(message["received_date"], today)
    urgency = urgency_model.predict([message["message_text"]])[0]
    tone_read = read_tone(message["message_text"], cache_path)
    tone = tone_read["tone"]

    decided = decide_escalation(age_days, urgency, tone)

    return {
        "message_id": message["message_id"], "age_days": age_days, "urgency": urgency,
        "tone": tone, "escalate": decided["escalate"], "signals": decided["signals"],
    }


def write_escalations(messages, urgency_model, escalations_path, today=None,
                       cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    def handle_one(message):
        return escalate_one_message(message, urgency_model, today, cache_path)

    results = run_batch(messages, handle_one, constants.BATCH_FAILURES_PATH)

    escalations_path = Path(escalations_path)
    escalations_path.parent.mkdir(parents=True, exist_ok=True)

    decided = failed = escalated = 0
    with open(escalations_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ESCALATION_FIELDS)
        for one in results:
            if isinstance(one, MessageFailure):
                failed += 1
                continue
            decided += 1
            if one["escalate"]:
                escalated += 1
            writer.writerow((
                one["message_id"], one["age_days"], one["urgency"], one["tone"],
                one["escalate"], ";".join(one["signals"]),
            ))

    return {"decided": decided, "failed": failed, "escalated": escalated}


if __name__ == "__main__":
    from metermind.exception_models.baseline_model import load_model

    corpus = pd.read_csv(constants.COMPLAINT_MESSAGES_PATH).head(constants.ESCALATION_SAMPLE_MESSAGES)
    urgency_model = load_model(constants.COMPLAINT_URGENCY_MODEL_PATH)

    counted = write_escalations(corpus.to_dict("records"), urgency_model, constants.ESCALATIONS_PATH)
    print(counted)
