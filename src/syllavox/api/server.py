"""
API server lifecycle.

Runs FastAPI/Uvicorn in a background thread so the Qt event loop can remain
on the main thread.
"""

from __future__ import annotations

import threading
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from syllavox.api.context import ApiContext
from syllavox.constants import (
    API_HOST,
    API_PORT,
    API_VERSION,
    PRODUCT_NAME,
    PROJECT_VERSION,
)
from syllavox.api.security import ALLOWED_ORIGINS, OriginGuardMiddleware
from syllavox.api.routes import create_router

class ApiServer:
    """
    Local API server lifecycle manager.

    Responsibilities:
    - create FastAPI app
    - configure CORS
    - run Uvicorn in a background thread
    - stop cleanly on application shutdown
    """

    def __init__(
        self,
        context: ApiContext,
        host: str = API_HOST,
        port: int = API_PORT,
    ) -> None:
        # Security invariant: API must only bind to localhost.
        if host != API_HOST:
            raise ValueError(
                f"API host must be {API_HOST!r}, got {host!r}."
            )

        self._context = context
        self._host = host
        self._port = port

        self._app: FastAPI = self._create_app()
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}/{API_VERSION}"

    def _create_app(self) -> FastAPI:
        app = FastAPI(
            title=f"{PRODUCT_NAME} API",
            version=PROJECT_VERSION,
            docs_url=f"/{API_VERSION}/docs",
            redoc_url=f"/{API_VERSION}/redoc",
            openapi_url=f"/{API_VERSION}/openapi.json",
        )

        self._configure_cors(app)
        self._configure_routes(app)

        return app

    def _configure_cors(self, app: FastAPI) -> None:
        """
        Allows localhost development origins only.
        Requests with no Origin header are handled by OriginGuardMiddleware.
        """
        app.add_middleware(
            CORSMiddleware,
            allow_origins=sorted(ALLOWED_ORIGINS),
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        )

        app.add_middleware(
            OriginGuardMiddleware,
            logger=self._context.logger,
        )

    def _configure_routes(self, app: FastAPI) -> None:
        """
        Register API routes.
        """
        app.include_router(create_router(self._context))
        self._context.logger.info("API routes registered")

    def start(self) -> None:
        """
        Start Uvicorn in a background daemon thread.

        Safe to call once. If already running, it does nothing.
        """
        if self._thread is not None and self._thread.is_alive():
            self._context.logger.warning("API server already running")
            return

        config = uvicorn.Config(
            app=self._app,
            host=self._host,
            port=self._port,
            log_level="info",
            access_log=False,
            # The desktop application owns file logging. Uvicorn's default
            # formatter assumes console streams exist, which is not true for
            # PyInstaller's --windowed builds.
            log_config=None,
        )

        self._server = uvicorn.Server(config)

        self._thread = threading.Thread(
            target=self._server.run,
            name="SyllavoxApiServer",
            daemon=True,
        )

        self._thread.start()

        self._context.logger.info(
            "API server starting at http://%s:%s/%s",
            self._host,
            self._port,
            API_VERSION,
        )

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """
        Request clean API server shutdown.
        """
        if self._server is None:
            return

        self._context.logger.info("Stopping API server")

        self._server.should_exit = True

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)

        self._context.logger.info("API server stopped")
