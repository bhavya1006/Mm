"""The reading store backed by SQLite through the mapping of Week 2 Day 5."""

from config import constants
from metermind.api.orm_models import ReadingRow, build_session_factory
from metermind.api.repository import STORED_READING_FIELDS, ReadingRepository
from metermind.core.exceptions import ReadingStorageError


class SqlReadingRepository(ReadingRepository):
    def __init__(self, database_path=constants.READINGS_DATABASE_PATH):
        self.database_path = str(database_path)
        self._session_factory = build_session_factory(self.database_path)

    def _next_identifier(self, session):
        highest = (
            session.query(ReadingRow.reading_id)
            .order_by(ReadingRow.reading_id.desc())
            .first()
        )
        if highest is None:
            return "RDG00000001"
        return f"RDG{int(highest[0].replace('RDG', '')) + 1:08d}"

    def _as_dict(self, row):
        return {field: getattr(row, field) for field in STORED_READING_FIELDS}

    def add_reading(self, reading):
        with self._session_factory() as session:
            identifier = self._next_identifier(session)
            row = ReadingRow(reading_id=identifier, **{
                field: reading.get(field) for field in STORED_READING_FIELDS
                if field != "reading_id"
            })
            session.add(row)
            session.commit()
            return self._as_dict(row)

    def get_reading(self, reading_identifier):
        with self._session_factory() as session:
            row = session.get(ReadingRow, reading_identifier)
            if row is None:
                raise ReadingStorageError(f"there is no reading {reading_identifier}")
            return self._as_dict(row)

    def replace_reading(self, reading_identifier, reading):
        with self._session_factory() as session:
            row = session.get(ReadingRow, reading_identifier)
            if row is None:
                raise ReadingStorageError(f"there is no reading {reading_identifier}")
            for field in STORED_READING_FIELDS:
                if field != "reading_id":
                    setattr(row, field, reading.get(field))
            session.commit()
            return self._as_dict(row)

    def list_readings(self):
        with self._session_factory() as session:
            rows = session.query(ReadingRow).order_by(ReadingRow.reading_id).all()
            return [self._as_dict(row) for row in rows]

    def remove_reading(self, reading_identifier):
        with self._session_factory() as session:
            row = session.get(ReadingRow, reading_identifier)
            if row is None:
                raise ReadingStorageError(f"there is no reading {reading_identifier}")
            session.delete(row)
            session.commit()
