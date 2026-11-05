# `metermind.assistant`

The assistant is a checkpointed LangGraph workflow for consumer questions about readings, bills, exceptions, and tariffs.

- `__init__.py`: package marker.
- `agents.py`: prompt templates and model-backed planning, drafting, critique, and response functions.
- `graph.py`: wires triage, planning, tools, drafting, critique, approval gate, and response nodes into a graph.
- `nodes.py`: triages questions, executes planned tools, and holds unsafe/unsupported answers for review.
- `state.py`: defines the typed assistant state, identifies accumulating `steps`/`tool_calls` channels, and creates initial state for a question.
- `tools.py`: exposes reading lookup, bill calculation, exception prediction, and tariff-order search tools with Pydantic argument schemas.
- `workflow.py`: opens a SQLite-backed graph checkpoint store, invokes a thread, serializes outcomes, and releases held runs.

The FastAPI assistant router is documented in [../../FASTAPI.md](../../FASTAPI.md). Model-backed tools depend on prepared database/model/vector-store artifacts.
