"""The reading book on disk, as CSV."""

import csv
from pathlib import Path

from metermind.core.entities import create_service_connection
from metermind.core.exceptions import ReadingStorageError, UnsupportedCategoryError


class ReadingFileStorage:
    def __init__(self, directory):
        self.directory = Path(directory)

    def save_readings_csv(self, file_name, readings):
        if not readings:
            raise ReadingStorageError("cannot write an empty list of readings")

        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / file_name

        fieldnames = list(readings[0].keys())
        with open(file_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(readings)

        return file_path

    def load_readings_csv(self, file_name):
        file_path = self.directory / file_name
        if not file_path.exists():
            raise ReadingStorageError(f"no such file: {file_path}")

        with open(file_path, newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def load_connection_objects(self, file_name):
        connections = []
        for record in self.load_readings_csv(file_name):
            try:
                connections.append(create_service_connection(record))
            except (UnsupportedCategoryError, KeyError, ValueError, TypeError):
                continue
        return connections


if __name__ == "__main__":
    storage = ReadingFileStorage("data")
    connections = storage.load_connection_objects("reading_book_predict.csv")
    print(f"connections loaded: {len(connections)}")
