"""An answer is only as good as what it cites, and it may cite only what was retrieved."""

import csv
from pathlib import Path
import re

from config import constants

CITATION_PATTERN = re.compile(r"\[([A-Za-z0-9\-]+)\]")
ANSWER_FIELDS = ("question_id", "question", "answer", "citations", "chunks_handed_over")

ANSWER_PROMPT = (
    "Answer the question using ONLY the extracts below, each marked with its identifier in "
    "square brackets. Cite the identifier of every extract you rely on, in square brackets, "
    "right after the fact it supports. If the extracts do not answer the question, reply "
    "exactly with: {unanswerable}\n\n"
    "{extracts}\n\n"
    "Question: {question}\n\n"
    "Reply with a JSON object and nothing else, holding two keys: \"answer\" and \"citations\" "
    "(a list of the identifiers you cited)."
)


class UngroundedAnswer(Exception):
    pass


def build_answer_prompt(question, chunks):
    if not chunks:
        raise UngroundedAnswer(
            "nothing was retrieved for this question, so there is nothing to build a prompt from"
        )

    extracts = "\n\n".join(f"[{one['chunk_id']}] {one['text']}" for one in chunks)
    return ANSWER_PROMPT.format(
        unanswerable=constants.UNANSWERABLE_REPLY, extracts=extracts, question=question
    )


def check_citations(answer_text, chunks):
    valid_ids = {one["chunk_id"] for one in chunks}
    resolved = []
    for one in CITATION_PATTERN.findall(answer_text):
        if one not in valid_ids:
            raise UngroundedAnswer(f"the answer cites {one}, which was never handed over")
        if one not in resolved:
            resolved.append(one)
    return resolved


def answer_from_chunks(question, chunks, cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    from metermind.message_intelligence.llm_client import ask_model, read_answer

    prompt = build_answer_prompt(question, chunks)
    answered = ask_model(prompt, cache_path)
    read = read_answer(answered, constants.GROUNDED_ANSWER_KEYS)
    answer_text = read["answer"]

    if answer_text.strip() == constants.UNANSWERABLE_REPLY:
        raise UngroundedAnswer("the extracts retrieved do not answer this question")

    citations = check_citations(answer_text, chunks)
    return {"answer": answer_text, "citations": citations}


def write_answers(asked, collection, embedder, answers_path,
                   cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    from metermind.message_intelligence.llm_client import LanguageModelError
    from metermind.retrieval.vector_store import search_tariff

    answers_path = Path(answers_path)
    answers_path.parent.mkdir(parents=True, exist_ok=True)

    answered_count = refused_count = 0
    with open(answers_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ANSWER_FIELDS)

        for one in asked:
            chunks = search_tariff(collection, one["question"], embedder)
            handed_over = ";".join(chunk["chunk_id"] for chunk in chunks)
            try:
                result = answer_from_chunks(one["question"], chunks, cache_path)
                answered_count += 1
                writer.writerow((
                    one["question_id"], one["question"], result["answer"],
                    ";".join(result["citations"]), handed_over,
                ))
            except (UngroundedAnswer, LanguageModelError):
                refused_count += 1
                writer.writerow((one["question_id"], one["question"], "", "", handed_over))

    return {"questions": len(asked), "answered": answered_count, "refused": refused_count}


if __name__ == "__main__":
    import json

    from metermind.retrieval.vector_store import load_embedder, open_tariff_store

    asked = json.loads(Path(constants.RETRIEVAL_EVALUATION_SET_PATH).read_text(encoding="utf-8"))
    collection = open_tariff_store(constants.TARIFF_STORE_DIRECTORY)
    embedder = load_embedder()

    counted = write_answers(asked, collection, embedder, constants.TARIFF_ANSWERS_PATH)
    print(counted)
