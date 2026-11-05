# `metermind`

This package contains the application domain and service layers. The package itself has no behavior in `__init__.py`; behavior is split into API, core billing, data access, ML exception handling, message intelligence, retrieval, and assistant workflows.

## Directories

- [api/README.md](api/README.md): FastAPI application, schemas, auth, persistence, and routers.
- [assistant/README.md](assistant/README.md): stateful LangGraph assistant and tools.
- [core/README.md](core/README.md): billing domain and validation.
- [data_access/README.md](data_access/README.md): file and database pipelines.
- [exception_models/README.md](exception_models/README.md): exception classifiers and queues.
- [message_intelligence/README.md](message_intelligence/README.md): complaint and conversation processing.
- [retrieval/README.md](retrieval/README.md): tariff-document retrieval and grounded answers.
