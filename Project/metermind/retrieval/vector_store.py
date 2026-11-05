"""A collection of chunks embedded and stored, and the search over it."""

import json
from pathlib import Path

import chromadb

from config import constants

STORE_SETTINGS = {"hnsw:space": constants.VECTOR_DISTANCE_MEASURE}
SEARCH_RESULT_FIELDS = ("chunk_id", "text", "distance") + constants.STORED_CHUNK_FIELDS


class TariffStoreMissing(Exception):
    pass


def load_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(constants.EMBEDDING_MODEL_NAME)


def build_tariff_store(chunks_path, store_directory, embedder):
    chunks = json.loads(Path(chunks_path).read_text(encoding="utf-8"))

    client = chromadb.PersistentClient(path=str(store_directory))
    try:
        client.delete_collection(constants.TARIFF_STORE_COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(constants.TARIFF_STORE_COLLECTION, metadata=STORE_SETTINGS)

    texts = [one["text"] for one in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()
    ids = [one["chunk_id"] for one in chunks]
    metadatas = [{field: one[field] for field in constants.STORED_CHUNK_FIELDS} for one in chunks]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return collection


def open_tariff_store(store_directory):
    client = chromadb.PersistentClient(path=str(store_directory))
    try:
        return client.get_collection(constants.TARIFF_STORE_COLLECTION)
    except Exception:
        raise TariffStoreMissing(f"no tariff store was found at {store_directory}")


def _read_results(found):
    results = []
    for position in range(len(found["ids"][0])):
        entry = {
            "chunk_id": found["ids"][0][position],
            "text": found["documents"][0][position],
            "distance": found["distances"][0][position],
        }
        entry.update(found["metadatas"][0][position])
        results.append(entry)
    return results


def search_tariff(collection, query_text, embedder, result_count=None):
    wanted = result_count if result_count is not None else constants.SEARCH_RESULT_COUNT
    query_embedding = embedder.encode([query_text], show_progress_bar=False).tolist()
    found = collection.query(query_embeddings=query_embedding, n_results=wanted)
    return _read_results(found)


if __name__ == "__main__":
    embedder = load_embedder()
    collection = build_tariff_store(constants.TARIFF_CHUNKS_PATH, constants.TARIFF_STORE_DIRECTORY, embedder)
    print(f"stored: {collection.count()} chunks")

    found = search_tariff(collection, "what is the fixed charge for each kilowatt", embedder)
    for one in found:
        print(f"{one['distance']:.3f}  {one['chunk_id']}  {one['section']}")
