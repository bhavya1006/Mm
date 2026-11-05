"""A question about a bill has to be answered out of the order that governed that bill."""

import csv
from pathlib import Path

from config import constants
from metermind.retrieval.grounded_answer import ANSWER_FIELDS

FILTERED_ANSWER_FIELDS = ANSWER_FIELDS + ("order_in_force",)


class NoOrderInForce(Exception):
    pass


def order_in_force(manifest, consumer_category, billing_period):
    as_of = f"{billing_period}-01"
    for entry in manifest:
        if entry["consumer_category"] != consumer_category:
            continue
        if entry["effective_from"] <= as_of <= entry["effective_to"]:
            return entry
    raise NoOrderInForce(
        f"no {consumer_category} order was in force during {billing_period}"
    )


def filtered_search(collection, query_text, embedder, consumer_category, billing_period,
                     manifest, result_count=None):
    from metermind.retrieval.vector_store import _read_results

    order = order_in_force(manifest, consumer_category, billing_period)
    wanted = result_count if result_count is not None else constants.SEARCH_RESULT_COUNT

    query_embedding = embedder.encode([query_text], show_progress_bar=False).tolist()
    found = collection.query(
        query_embeddings=query_embedding, n_results=wanted, where={"order_id": order["order_id"]}
    )
    return _read_results(found)


def write_filtered_answers(asked, collection, embedder, answers_path, manifest,
                            cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    from metermind.message_intelligence.llm_client import LanguageModelError
    from metermind.retrieval.grounded_answer import UngroundedAnswer, answer_from_chunks

    answers_path = Path(answers_path)
    answers_path.parent.mkdir(parents=True, exist_ok=True)

    answered_count = refused_count = 0
    with open(answers_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FILTERED_ANSWER_FIELDS)

        for one in asked:
            order = order_in_force(manifest, one["consumer_category"], one["billing_period"])
            chunks = filtered_search(
                collection, one["question"], embedder, one["consumer_category"],
                one["billing_period"], manifest,
            )
            handed_over = ";".join(chunk["chunk_id"] for chunk in chunks)
            try:
                result = answer_from_chunks(one["question"], chunks, cache_path)
                answered_count += 1
                writer.writerow((
                    one["question_id"], one["question"], result["answer"],
                    ";".join(result["citations"]), handed_over, order["order_id"],
                ))
            except (UngroundedAnswer, LanguageModelError):
                refused_count += 1
                writer.writerow((
                    one["question_id"], one["question"], "", "", handed_over, order["order_id"],
                ))

    return {"questions": len(asked), "answered": answered_count, "refused": refused_count}


if __name__ == "__main__":
    import json

    from metermind.retrieval.document_loader import read_manifest
    from metermind.retrieval.vector_store import load_embedder, open_tariff_store

    asked = json.loads(Path(constants.RETRIEVAL_EVALUATION_SET_PATH).read_text(encoding="utf-8"))
    collection = open_tariff_store(constants.TARIFF_STORE_DIRECTORY)
    embedder = load_embedder()
    manifest = read_manifest()

    counted = write_filtered_answers(
        asked, collection, embedder, constants.FILTERED_ANSWERS_PATH, manifest
    )
    print(counted)
