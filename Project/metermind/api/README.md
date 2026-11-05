# `metermind.api`

The API package owns HTTP composition, request/response contracts, authentication, middleware, case transitions, and reading persistence.

## Files

- `__init__.py`: package marker; no runtime behavior.
- `access_control.py`: issues and verifies HS256 JWTs, enforces signed-in/inspector access, and appends case-transition audit records.
- `application_factory.py`: builds the FastAPI app, mounts all routers under `/api/v1`, chooses in-memory versus SQL reading storage, and installs middleware.
- `case_transitions.py`: defines the allowed case-status ladder and rejects illegal moves.
- `middleware.py`: logs request metadata, rate-limits by client IP, and configures CORS.
- `orm_models.py`: SQLAlchemy mappings for `connections` and `readings`; creates the SQLite schema and session factory.
- `password_hashing.py`: Argon2 password hashing and verification helpers used by account sign-up/login; plaintext passwords are not stored.
- `repository.py`: abstract reading-store interface plus the process-local in-memory implementation.
- `schemas.py`: Pydantic request and response models, field constraints, normalization, and date parsing.
- `sql_repository.py`: repository implementation that stores and retrieves `ReadingRow` records through SQLAlchemy.
- `routers/`: HTTP route modules; see [routers/README.md](routers/README.md).

The API does not store calculated charge fields in the reading row. Router responses recalculate billing through `metermind.core.entities`.
