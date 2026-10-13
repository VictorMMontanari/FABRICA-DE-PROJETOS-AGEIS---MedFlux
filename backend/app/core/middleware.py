"""Middleware de contexto da requisição: request_id, log de acesso e captura de erros inesperados."""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.core.exceptions import error_body
from app.core.logging import get_logger, request_id_ctx

logger = get_logger("app.request")

# Healthchecks do Docker rodam a cada poucos segundos: não poluem o log.
_QUIET_PATHS = frozenset({"/healthz", "/readyz"})


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_ctx.set(request_id[:64])
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Erro não tratado: loga com stack trace e devolve 500 padronizado, sem vazar detalhes.
            logger.exception("unhandled_error", extra={"method": request.method, "path": request.url.path})
            response = JSONResponse(error_body("internal_error", "Erro interno no servidor."), status_code=500)
        finally:
            request_id_ctx.reset(token)

        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers["X-Request-ID"] = request_id[:64]
        if request.url.path in _QUIET_PATHS:
            return response
        logger.info(
            "request",
            extra={
                "request_id": request_id[:64],
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
