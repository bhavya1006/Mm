"""The in-memory reading store, and the interface every store answers."""

import abc

from metermind.core.exceptions import ReadingStorageError

STORED_READING_FIELDS = (
    "reading_id",
    "account_number",
    "meter_serial",
    "consumer_category",
    "billing_period",
    "sanctioned_load_kw",
    "cycle_days",
    "previous_reading",
    "current_reading",
    "read_type",
    "case_status",
)


class ReadingRepository(abc.ABC):
    @abc.abstractmethod
    def add_reading(self, reading):
        ...

    @abc.abstractmethod
    def get_reading(self, reading_identifier):
        ...

    @abc.abstractmethod
    def replace_reading(self, reading_identifier, reading):
        ...

    @abc.abstractmethod
    def list_readings(self):
        ...

    @abc.abstractmethod
    def remove_reading(self, reading_identifier):
        ...


class InMemoryReadingRepository(ReadingRepository):
    def __init__(self):
        self._readings = {}
        self._next_number = 1

    def _issue_identifier(self):
        identifier = f"RDG{self._next_number:08d}"
        self._next_number += 1
        return identifier

    def _settled(self, reading_identifier, reading):
        stored = {field: reading.get(field) for field in STORED_READING_FIELDS
                 if field != "reading_id"}
        stored["reading_id"] = reading_identifier
        return stored

    def add_reading(self, reading):
        identifier = self._issue_identifier()
        stored = self._settled(identifier, reading)
        self._readings[identifier] = stored
        return dict(stored)

    def get_reading(self, reading_identifier):
        if reading_identifier not in self._readings:
            raise ReadingStorageError(f"there is no reading {reading_identifier}")
        return dict(self._readings[reading_identifier])

    def replace_reading(self, reading_identifier, reading):
        if reading_identifier not in self._readings:
            raise ReadingStorageError(f"there is no reading {reading_identifier}")
        stored = self._settled(reading_identifier, reading)
        self._readings[reading_identifier] = stored
        return dict(stored)

    def list_readings(self):
        return [dict(one) for one in self._readings.values()]

    def remove_reading(self, reading_identifier):
        if reading_identifier not in self._readings:
            raise ReadingStorageError(f"there is no reading {reading_identifier}")
        del self._readings[reading_identifier]
