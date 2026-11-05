"""The tariff orders, read off the PDF and dated by the manifest."""

import json
from pathlib import Path

from config import constants


class UnreadableOrder(Exception):
    pass


def read_pdf_text(pdf_path):
    path = Path(pdf_path)
    if not path.exists():
        raise UnreadableOrder(f"no such file: {path}")

    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as failed:
        raise UnreadableOrder(f"{path} could not be read: {failed}")

    text = "\n".join(pages_text).strip()
    if not text:
        raise UnreadableOrder(f"{path} yielded no text")

    return text


def read_manifest(manifest_path=constants.TARIFF_ORDERS_MANIFEST_PATH):
    return json.loads(Path(manifest_path).read_text(encoding="utf-8"))


def load_tariff_orders(orders_directory=constants.TARIFF_ORDERS_DIRECTORY,
                        manifest_path=constants.TARIFF_ORDERS_MANIFEST_PATH):
    manifest = read_manifest(manifest_path)

    orders = []
    for entry in manifest:
        pdf_path = Path(orders_directory) / entry["file_name"]
        text = read_pdf_text(pdf_path)
        orders.append({**entry, "text": text})
    return orders


if __name__ == "__main__":
    orders = load_tariff_orders()
    total_characters = sum(len(one["text"]) for one in orders)
    print(f"{len(orders)} orders, {total_characters} characters of text")
