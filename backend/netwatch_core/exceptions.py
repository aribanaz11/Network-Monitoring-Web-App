"""
NetWatch Standardized RFC 7807 Problem Details Exception Handler
Formats all REST API errors into predictable, secure, machine-readable JSON structures.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger('netwatch.exceptions')

def custom_exception_handler(exc, context):
    """
    RFC 7807 compliant Problem Details exception handler.
    Returns:
    {
        "type": "https://api.netwatch.io/errors/<error_slug>",
        "title": "<Human-readable title>",
        "status": <HTTP status code>,
        "detail": "<Specific error detail>",
        "instance": "<Request path>",
        "invalid_params": [...] (optional for validation errors)
    }
    """
    # Call REST framework's default exception handler first to get the standard response
    response = exception_handler(exc, context)
    request = context.get('request')
    path = request.path if request else '/api/'

    if response is not None:
        status_code = response.status_code
        data = response.data

        # Determine error title and slug
        if status_code == status.HTTP_400_BAD_REQUEST:
            slug = "bad-request"
            title = "Invalid Request Parameters"
        elif status_code == status.HTTP_401_UNAUTHORIZED:
            slug = "unauthorized"
            title = "Authentication Required"
        elif status_code == status.HTTP_403_FORBIDDEN:
            slug = "forbidden"
            title = "Permission Denied"
        elif status_code == status.HTTP_404_NOT_FOUND:
            slug = "not-found"
            title = "Resource Not Found"
        elif status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            slug = "method-not-allowed"
            title = "HTTP Method Not Allowed"
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            slug = "rate-limit-exceeded"
            title = "Rate Limit Exceeded"
        else:
            slug = "client-error"
            title = "Client Error"

        # Format details
        invalid_params = None
        if isinstance(data, dict):
            if 'detail' in data:
                detail_str = str(data['detail'])
            else:
                detail_str = "One or more validation constraints failed."
                invalid_params = [
                    {'name': k, 'reason': str(v[0] if isinstance(v, list) else v)}
                    for k, v in data.items()
                ]
        elif isinstance(data, list):
            detail_str = str(data[0]) if data else "An error occurred."
        else:
            detail_str = str(data)

        problem_payload = {
            "type": f"https://api.netwatch.io/errors/{slug}",
            "title": title,
            "status": status_code,
            "detail": detail_str,
            "instance": path
        }
        if invalid_params:
            problem_payload["invalid_params"] = invalid_params

        response.data = problem_payload
        return response

    # Handle unhandled server errors (HTTP 500) gracefully without leaking secrets
    logger.exception(f"Unhandled Internal Server Error processing request {path}: {exc}")
    return Response(
        {
            "type": "https://api.netwatch.io/errors/internal-server-error",
            "title": "Internal Server Error",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "An unexpected error occurred on the server. The incident has been logged.",
            "instance": path
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
