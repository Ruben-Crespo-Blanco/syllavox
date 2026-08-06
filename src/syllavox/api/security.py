"""
API security helpers.

Current policy:
- allow missing Origin headers
- allow localhost development origins
- allow browser extension origins during development
- reject other origins

Later, extension origins should be restricted to exact known extension IDs.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from syllavox.api.errors import ErrorCode, make_error


ALLOWED_ORIGINS = {
    "http://localhost",
    "http://127.0.0.1",
    "http://127.0.0.1:8765",
    "http://localhost:8765",
}

ALLOWED_EXTENSION_SCHEMES = {
    "chrome-extension",
    "moz-extension",
}


def is_allowed_origin(origin: str | None) -> bool:
    """
    Return True if the request Origin is allowed.

    Rules:
    - Missing Origin is allowed.
    - Localhost development origins are allowed.
    - Chrome/Edge extension origins are allowed during development.
    - Firefox extension origins are allowed during development.
    """
    if origin is None:
        return True

    if origin in ALLOWED_ORIGINS:
        return True

    parsed = urlparse(origin)

    if parsed.scheme in ALLOWED_EXTENSION_SCHEMES:
        return True

    return False


class OriginGuardMiddleware(BaseHTTPMiddleware):
    """
    Reject requests from disallowed Origin headers.

    This supplements CORS. CORS protects browser behavior, while this guard also
    makes the server explicitly reject unwanted origins.
    """

    def __init__(self, app, logger) -> None:
        super().__init__(app)
        self._logger = logger

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")

        if not is_allowed_origin(origin):
            self._logger.warning(
                "Rejected request from forbidden origin: %s",
                origin,
            )

            return JSONResponse(
                status_code=403,
                content={
                    "status": "rejected",
                    "requestId": None,
                    "error": make_error(
                        ErrorCode.FORBIDDEN_ORIGIN,
                        "Request origin is not allowed.",
                    ),
                },
            )

        return await call_next(request)