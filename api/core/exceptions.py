import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import ErrorDetail, ParseError, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

HTTP_422 = 422


def error_response(status_code: int, detail: Any) -> Response:
    return Response({"detail": detail}, status=status_code)


def _flatten_validation_errors(detail: Any, loc: list[str | int]) -> list[dict[str, Any]]:
    if isinstance(detail, dict):
        errors: list[dict[str, Any]] = []
        for key, value in detail.items():
            child_loc = loc if key == "non_field_errors" else [*loc, key]
            errors.extend(_flatten_validation_errors(value, child_loc))
        return errors

    if isinstance(detail, list):
        if all(isinstance(item, (str, ErrorDetail)) for item in detail):
            return [_error_entry(item, loc) for item in detail]
        errors = []
        for index, value in enumerate(detail):
            if value:
                errors.extend(_flatten_validation_errors(value, [*loc, index]))
        return errors

    return [_error_entry(detail, loc)]


def _error_entry(item: Any, loc: list[str | int]) -> dict[str, Any]:
    code = getattr(item, "code", None) or "value_error"
    return {"type": code, "loc": loc, "msg": str(item)}


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF exception handler that keeps the FastAPI error contract.

    Validation and JSON parse errors return 422 with a list of
    ``{"type", "loc", "msg"}`` entries under ``detail``; everything else
    returns ``{"detail": ...}``.
    """
    if isinstance(exc, ValidationError):
        return error_response(HTTP_422, _flatten_validation_errors(exc.detail, ["body"]))

    if isinstance(exc, ParseError):
        return error_response(
            HTTP_422,
            [{"type": "json_invalid", "loc": ["body"], "msg": str(exc.detail)}],
        )

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error")
    return response
