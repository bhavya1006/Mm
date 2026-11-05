"""A thread runs to a dozen turns and nobody reads all of them. The sentences that carry it
are found by attention, and nothing is invented."""

import csv
import re
from pathlib import Path

import numpy as np
import pandas as pd

from config import constants
from metermind.message_intelligence.attention import attention_weights

SENTENCE_END_PATTERN = re.compile(r"(?<=[.!?])\s+")
SHORTEST_SENTENCE_CHARACTERS = 20

_WORD_PATTERN = re.compile(r"[a-z0-9']+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


class UnreadableThread(Exception):
    pass


def split_sentences(thread_text):
    if not thread_text or not thread_text.strip():
        return []

    pieces = SENTENCE_END_PATTERN.split(thread_text.strip())
    sentences = []
    for piece in pieces:
        settled = _WHITESPACE_PATTERN.sub(" ", piece).strip()
        if len(settled) >= SHORTEST_SENTENCE_CHARACTERS:
            sentences.append(settled)
    return sentences


def sentence_matrix(sentences):
    tokenized = [_WORD_PATTERN.findall(one.lower()) for one in sentences]
    vocabulary = sorted({word for tokens in tokenized for word in tokens})
    index_by_word = {word: position for position, word in enumerate(vocabulary)}

    matrix = np.zeros((len(sentences), max(len(vocabulary), 1)))
    for row, tokens in enumerate(tokenized):
        for word in tokens:
            matrix[row, index_by_word[word]] += 1
    return matrix


def score_sentences(sentences):
    if len(sentences) < 2:
        raise UnreadableThread("a thread needs at least two sentences to compare")

    matrix = sentence_matrix(sentences)
    weights = attention_weights(matrix, matrix)
    return weights.sum(axis=0)


def summarise_thread(thread_text, sentence_count=None):
    wanted = sentence_count if sentence_count is not None else constants.SUMMARY_SENTENCE_COUNT

    sentences = split_sentences(thread_text)
    if not sentences:
        raise UnreadableThread("this thread has no sentence long enough to summarise")

    if len(sentences) <= wanted:
        return " ".join(sentences)

    scores = score_sentences(sentences)
    ranked = sorted(range(len(sentences)), key=lambda index: scores[index], reverse=True)
    chosen = sorted(ranked[:wanted])
    return " ".join(sentences[index] for index in chosen)


def write_thread_summaries(threads_path, summaries_path):
    from metermind.message_intelligence.text_cleaning import clean_message

    threads = pd.read_csv(threads_path)
    summaries_path = Path(summaries_path)
    summaries_path.parent.mkdir(parents=True, exist_ok=True)

    seen = summarised = not_summarised = 0
    with open(summaries_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("thread_id", "turns", "summary"))

        for thread_id, group in threads.groupby("thread_id", sort=False):
            seen += 1
            ordered = group.sort_values("turn_number")
            joined = " ".join(clean_message(one) for one in ordered["message_text"])

            try:
                summary = summarise_thread(joined)
                summarised += 1
            except UnreadableThread as refused:
                summary = f"could not be summarised: {refused}"
                not_summarised += 1

            writer.writerow((thread_id, len(ordered), summary))

    return {"threads": seen, "summarised": summarised, "not summarised": not_summarised}


if __name__ == "__main__":
    counted = write_thread_summaries(constants.MESSAGE_THREADS_PATH, constants.THREAD_SUMMARIES_PATH)
    print(f"written: {counted}")
