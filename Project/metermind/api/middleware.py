"""The layers every request passes through."""

import time
from collections import defaultdict
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import constants

REQUEST_LOG_FIELDS = ("received_at", "method", "path", "status_code", "duration_ms")


class RequestLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, application, log_path=constants.REQUEST_LOG_PATH):
        super().__init__(application)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def dispatch(self, request, call_next):
        received_at = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - received_at) * 1000
        fields = (
            f"{received_at:.3f}",
            request.method,
            request.url.path,
            str(response.status_code),
            f"{duration_ms:.1f}",
        )
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write("|".join(fields) + "\n")
        return response


class FixedWindowRateLimiter(BaseHTTPMiddleware):
    def __init__(self, application, allowed=constants.REQUESTS_ALLOWED_PER_WINDOW,
                 window_seconds=constants.RATE_LIMIT_WINDOW_SECONDS):
        super().__init__(application)
        self.allowed = allowed
        self.window_seconds = window_seconds
        self._counts = defaultdict(lambda: [None, 0])

    async def dispatch(self, request, call_next):
        caller = request.client.host if request.client else "unknown"
        current_window = int(time.time() // self.window_seconds)
        window_start, count = self._counts[caller]

        if window_start != current_window:
            window_start, count = current_window, 0

        count += 1
        self._counts[caller] = [window_start, count]

        if count > self.allowed:
            return JSONResponse({"detail": "too many requests, try again later"},
                                status_code=429)

        return await call_next(request)


def add_cross_origin_policy(application):
    from fastapi.middleware.cors import CORSMiddleware

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(constants.ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    return application


if __name__ == "__main__":
    print(f"fields written for every request: {REQUEST_LOG_FIELDS}")
    print(
        f"{constants.REQUESTS_ALLOWED_PER_WINDOW} requests are allowed in each "
        f"{constants.RATE_LIMIT_WINDOW_SECONDS} second window"
    )
    print(f"origins the browser may call from: {constants.ALLOWED_ORIGINS}")
