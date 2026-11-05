# API routers

Each router is included by `application_factory.py` with the `/api/v1` prefix.

- `__init__.py`: router package marker.
- `assistant.py`: exposes assistant questions for any signed-in caller and release of held assistant threads for inspectors.
- `readings.py`: submits, reads, replaces, deletes, lists, prices readings, and changes case status. It delegates storage to the configured repository and billing to `create_service_connection`.
- `screening.py`: accepts a model-feature-rich reading, loads the champion exception model and operating rule, predicts an exception class/confidence, and selects an investigation queue.
- `user_accounts.py`: provides process-local account creation and login. It hashes passwords and returns signed bearer JWTs.

Route details, payloads, access control, status codes, and a complete sequence are in [../../../FASTAPI.md](../../../FASTAPI.md).
