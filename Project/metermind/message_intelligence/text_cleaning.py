"""A complaint carries a quoted reply, a greeting, a sign-off and a signature block. None of
that is the complaint."""

import re
from pathlib import Path

import pandas as pd

from config import constants

QUOTED_REPLY_PATTERN = re.compile(
    r"(?m)^[ \t]*(>.*|On .{0,80}(wrote|said):.*|-{2,}\s*Original Message\s*-{2,}.*)$"
)
GREETING_PATTERN = re.compile(
    r"(?i)^\s*(dear\s+(sir|madam|sir\s*/\s*madam|team|customer|sir/madam)|"
    r"to\s+whom(so)?ever\s+it\s+may\s+concern|respected\s+sir|hi|hello|greetings)"
    r"\s*[,.:!]*\s*$"
)
SIGN_OFF_PATTERN = re.compile(
    r"(?i)^\s*(thanks?(\s+(and|&)\s+regards)?|regards|best(\s+regards)?|sincerely|"
    r"yours\s+(faithfully|sincerely|truly)|warm\s+regards)\s*[,.:!]*\s*$"
)
SIGNATURE_PATTERN = re.compile(
    r"(?i)^\s*(mobile|phone|contact|tel|ph|cell)\s*(no\.?|number)?\s*[:.\-]?\s*\+?\d[\d\-\s]{6,}\s*$"
    r"|^\s*\+?\d{10,}\s*$"
)
COMPLAINT_REFERENCE_PATTERN = re.compile(constants.COMPLAINT_REFERENCE_PATTERN.strip("^$"))
WHITESPACE_PATTERN = re.compile(r"\s+")


def strip_quoted_reply(message):
    match = QUOTED_REPLY_PATTERN.search(message)
    if match:
        return message[:match.start()]
    return message


def strip_greeting_and_sign_off(message):
    lines = message.split("\n")
    kept = [
        line for line in lines
        if not GREETING_PATTERN.match(line) and not SIGN_OFF_PATTERN.match(line)
    ]
    return "\n".join(kept)


def strip_signature(message):
    lines = message.split("\n")
    kept = [line for line in lines if not SIGNATURE_PATTERN.match(line)]
    return "\n".join(kept)


def normalise_whitespace(message):
    return WHITESPACE_PATTERN.sub(" ", message).strip()


def clean_message(message):
    text = "" if message is None else str(message)
    text = strip_quoted_reply(text)
    text = strip_greeting_and_sign_off(text)
    text = strip_signature(text)
    text = COMPLAINT_REFERENCE_PATTERN.sub("", text)
    text = normalise_whitespace(text)
    return text


def clean_messages(messages):
    return [clean_message(one) for one in messages]


def clean_corpus(messages_path, clean_path):
    corpus = pd.read_csv(messages_path)
    corpus["clean_text"] = clean_messages(corpus["message_text"])

    clean_path = Path(clean_path)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    corpus.to_csv(clean_path, index=False)

    shortest = int(corpus["clean_text"].str.len().min())
    return {"messages": len(corpus), "shortest": shortest}


if __name__ == "__main__":
    counted = clean_corpus(constants.COMPLAINT_MESSAGES_PATH, constants.CLEAN_COMPLAINTS_PATH)
    print(counted)
