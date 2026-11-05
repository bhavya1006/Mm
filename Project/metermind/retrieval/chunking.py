"""Cuts the loaded orders into overlapping pieces, carrying the metadata that dates them."""

import json
from pathlib import Path

from config import constants

CHUNK_FIELDS = ("chunk_id", "text") + constants.STORED_CHUNK_FIELDS


def split_into_chunks(text, size=constants.CHUNK_CHARACTERS,
                       overlap=constants.CHUNK_OVERLAP_CHARACTERS):
    if overlap >= size:
        raise ValueError("the overlap must be smaller than the chunk size, or the cut never advances")

    pieces = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + size, text_length)
        piece = text[start:end]
        if piece.strip():
            pieces.append(piece)
        if end >= text_length:
            break
        start = end - overlap

    return pieces


def _section_heading_in(chunk_text, sections):
    found_at = -1
    found_section = ""
    for section in sections:
        position = chunk_text.find(section)
        if position != -1 and (found_at == -1 or position < found_at):
            found_at = position
            found_section = section
    return found_section


def chunk_metadata(order, chunk_text, position):
    chunk_id = f"{order['order_id']}-{position:03d}"
    return {
        "chunk_id": chunk_id,
        "text": chunk_text,
        "order_id": order["order_id"],
        "title": order["title"],
        "consumer_category": order["consumer_category"],
        "effective_from": order["effective_from"],
        "effective_to": order["effective_to"],
        "section": _section_heading_in(chunk_text, order.get("sections", [])),
    }


def write_chunks(orders, chunks_path=constants.TARIFF_CHUNKS_PATH):
    all_chunks = []
    without_a_section = 0

    for order in orders:
        pieces = split_into_chunks(order["text"])
        last_section = ""
        for position, piece in enumerate(pieces):
            entry = chunk_metadata(order, piece, position)
            if entry["section"]:
                last_section = entry["section"]
            else:
                entry["section"] = last_section
            if not entry["section"]:
                without_a_section += 1
            all_chunks.append(entry)

    chunks_path = Path(chunks_path)
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    chunks_path.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")

    return {"orders": len(orders), "chunks": len(all_chunks), "without_a_section": without_a_section}


if __name__ == "__main__":
    from metermind.retrieval.document_loader import load_tariff_orders

    orders = load_tariff_orders()
    counted = write_chunks(orders)
    print(counted)
