"""The clean reading book, stored and looked up as a database table."""

import sqlite3

import pandas as pd

from config import constants
from metermind.core.exceptions import ReadingStorageError

READINGS_TABLE = "readings"


class ReadingDatabase:
    def __init__(self, database_path):
        self.database_path = str(database_path)
        self.connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

    def create_readings_table(self, book):
        self.connection.execute(f"DROP TABLE IF EXISTS {READINGS_TABLE}")
        columns_sql = ", ".join(
            f'"{name}" TEXT PRIMARY KEY' if name == "reading_id" else f'"{name}" TEXT'
            for name in book.columns
        )
        self.connection.execute(f"CREATE TABLE {READINGS_TABLE} ({columns_sql})")
        book.to_sql(READINGS_TABLE, self.connection, index=False, if_exists="append")
        self.connection.commit()
        return len(book)

    def find_reading_by_identifier(self, reading_identifier):
        row = self.connection.execute(
            f"SELECT * FROM {READINGS_TABLE} WHERE reading_id = ?", (reading_identifier,)
        ).fetchone()
        return dict(row) if row is not None else None

    def delete_reading_by_identifier(self, reading_identifier):
        cursor = self.connection.execute(
            f"DELETE FROM {READINGS_TABLE} WHERE reading_id = ?", (reading_identifier,)
        )
        self.connection.commit()
        if cursor.rowcount == 0:
            raise ReadingStorageError(f"no such reading: {reading_identifier}")
        return cursor.rowcount


if __name__ == "__main__":
    book = pd.read_csv(constants.CLEAN_READING_BOOK_PATH)
    database = ReadingDatabase(constants.READINGS_DATABASE_PATH)
    stored = database.create_readings_table(book)
    print(f"stored: {stored}")
