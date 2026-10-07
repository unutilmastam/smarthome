"""API errors and handlers. Codes follow ARCHITECTURE 8."""

from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_body


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, details: Any = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def auth_required(message: str = "Authentication required") -> ApiError:
    return ApiError(401, "AUTH_REQUIRED", message)


def invalid_credentials() -> ApiError:
    return ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password")


def forbidden(message: str = "Not allowed") -> ApiError:
    return ApiError(403, "FORBIDDEN", message)


def not_found(what: str = "Resource") -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what} not found")


def conflict(message: str) -> ApiError:
    return ApiError(409, "CONFLICT", message)


def validation_error(message: str, details: Any = None) -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", message, details)


def rate_limited(retry_after: int) -> ApiError:
    return ApiError(
        429, "RATE_LIMITED", "Too many requests, try again later",
        headers={"Retry-After": str(max(1, retry_after))},
    )


_HTTP_CODES = {401: "AUTH_REQUIRED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(
            error_body(exc.code, exc.message, exc.details), status_code=exc.status,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        return JSONResponse(
            error_body("VALIDATION_ERROR", "Request validation failed", details), status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            error_body(code, str(exc.detail)), status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )
