# ============================================================
# utils/exceptions.py
# Custom exception hierarchy + FastAPI exception handlers.
# Keeps error handling consistent across every route.
# ============================================================

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ============================================================
# Base Application Exception
# ============================================================

class BTRSException(Exception):
    """
    Base class for all application-level exceptions.
    Carry an HTTP status code + user-facing message.
    """
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


# ============================================================
# 404 — Resource Not Found
# ============================================================

class BugNotFoundException(BTRSException):
    """Raised when a bug_id is not found in the database."""
    def __init__(self, bug_id: str):
        super().__init__(
            message=f"Bug with id '{bug_id}' was not found.",
            status_code=404,
        )


class UserNotFoundException(BTRSException):
    """Raised when a user_id is not found in the database."""
    def __init__(self, user_id: str):
        super().__init__(
            message=f"User with id '{user_id}' was not found.",
            status_code=404,
        )


class SuggestionNotFoundException(BTRSException):
    """Raised when no fix suggestion matches the given bug."""
    def __init__(self, bug_id: str):
        super().__init__(
            message=f"No fix suggestions found for bug id '{bug_id}'.",
            status_code=404,
        )


# ============================================================
# 400 — Bad Request / Validation
# ============================================================

class InvalidStatusTransitionException(BTRSException):
    """
    Raised when a requested FSM state transition is illegal.
    E.g. trying to move from 'new' directly to 'resolved'.
    """
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            message=(
                f"Invalid status transition: '{from_status}' → '{to_status}'. "
                f"Allowed path: new → assigned → in_progress → resolved."
            ),
            status_code=400,
        )


class BugAlreadyDeletedException(BTRSException):
    """Raised when operating on a soft-deleted bug."""
    def __init__(self, bug_id: str):
        super().__init__(
            message=f"Bug '{bug_id}' has been deleted and cannot be modified.",
            status_code=400,
        )


class BugAlreadyResolvedException(BTRSException):
    """Raised when trying to modify a resolved bug."""
    def __init__(self, bug_id: str):
        super().__init__(
            message=f"Bug '{bug_id}' is already resolved and cannot be changed.",
            status_code=400,
        )


class UserInactiveException(BTRSException):
    """Raised when assigning a bug to a deactivated user."""
    def __init__(self, user_id: str):
        super().__init__(
            message=f"User '{user_id}' is inactive and cannot be assigned bugs.",
            status_code=400,
        )


# ============================================================
# 409 — Conflict
# ============================================================

class DuplicateBugException(BTRSException):
    """Raised when an identical bug title+module already exists."""
    def __init__(self, title: str, module: str):
        super().__init__(
            message=f"A bug titled '{title}' in module '{module}' already exists.",
            status_code=409,
        )


# ============================================================
# FastAPI Exception Handlers
# Register these on the FastAPI app instance in main.py.
# ============================================================

def register_exception_handlers(app: FastAPI) -> None:
    """
    Attaches all custom exception handlers to the FastAPI app.
    Call once during application startup in main.py:
        register_exception_handlers(app)
    """

    @app.exception_handler(BTRSException)
    async def btrs_exception_handler(
        request: Request,
        exc: BTRSException,
    ) -> JSONResponse:
        logger.warning(
            "BTRS exception [%s] on %s %s — %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.message,
                    "detail": exc.detail,
                },
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "An unexpected internal server error occurred.",
                    "detail": str(exc) if True else "Internal server error",
                },
            },
        )