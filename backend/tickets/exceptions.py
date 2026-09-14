import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, JsonResponse
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class TicketAPIException(drf_exceptions.APIException):
    """Base class for the named token-lookup failures."""


class InvalidTokenError(TicketAPIException):
    status_code = 404
    default_detail = "This tracking link is not valid."
    default_code = "invalid_token"


class ExpiredTokenError(TicketAPIException):
    status_code = 410
    default_detail = "This tracking link has expired. Request a new one."
    default_code = "expired_token"


class RevokedTokenError(TicketAPIException):
    status_code = 410
    default_detail = "This tracking link has been revoked. Request a new one."
    default_code = "revoked_token"


def custom_exception_handler(exc, context):
    """One error shape everywhere: {"error": {"code", "message", "details"}}.
    Stack traces never cross the API boundary — an unhandled exception is
    logged in full server-side and reduced to a generic message here."""
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in API view")
        return Response(
            {"error": {"code": "server_error", "message": "An unexpected error occurred.", "details": {}}},
            status=500,
        )

    if isinstance(exc, drf_exceptions.ValidationError):
        code, message, details = "validation_error", "Validation failed.", response.data
    elif isinstance(exc, drf_exceptions.Throttled):
        code, message, details = "throttled", "Too many requests. Please try again later.", {}
    elif isinstance(
        exc,
        (
            drf_exceptions.NotAuthenticated,
            drf_exceptions.AuthenticationFailed,
            drf_exceptions.PermissionDenied,
            DjangoPermissionDenied,
        ),
    ):
        code, message, details = "permission_denied", "You do not have permission to perform this action.", {}
    elif isinstance(exc, (drf_exceptions.NotFound, Http404)):
        code, message, details = "not_found", str(getattr(exc, "detail", exc)), {}
    elif isinstance(exc, TicketAPIException):
        code, message, details = exc.default_code, str(exc.detail), {}
    else:
        code, message, details = getattr(exc, "default_code", "error"), str(getattr(exc, "detail", exc)), {}

    return Response({"error": {"code": code, "message": message, "details": details}}, status=response.status_code)


def csrf_failure(request, reason=""):
    return JsonResponse(
        {"error": {"code": "permission_denied", "message": "CSRF verification failed.", "details": {}}},
        status=403,
    )
