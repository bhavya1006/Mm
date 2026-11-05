# `metermind.data_access`

This package handles batch files and the SQLite reading book used by offline workflows and assistant tools.

- `__init__.py`: package marker.
- `cleaning_pipeline.py`: parses dates/numbers, checks required fields and physical plausibility, and writes clean and rejected CSV files.
- `database_loader.py`: creates a simple SQLite `readings` table from a clean pandas DataFrame and looks up/deletes readings by identifier.
- `database_reports.py`: runs grouped SQL reports for exception rates, estimated reads, and billed units, then writes a report file.
- `file_storage.py`: saves/loads reading CSVs and converts valid rows into domain connection objects.

This database loader is separate from the SQLAlchemy repository used by the FastAPI reading router. The assistant's `look_up_reading` tool uses this package's `ReadingDatabase`.
