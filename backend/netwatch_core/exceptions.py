import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('netwatch.exceptions')

def custom_exception_handler(exc, context):
    """
    Standardized Enterprise RFC-7807 problem details exception handler.
    Ensures every error response has consistent structure:
    {
        "type": "https://netwatch.io/errors/{error_code}",
        "title": "Error title",
        "status": 400/401/403/404/500,
        "detail": "Descriptive message",
        "errors": { ... field errors ... } or null
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "title": exc.__class__.__name__,
            "status": response.status_code,
            "detail": None,
            "errors": None
        }

        if isinstance(response.data, dict):
            if "detail" in response.data:
                custom_data["detail"] = response.data["detail"]
            else:
                custom_data["detail"] = "One or more validation errors occurred."
                custom_data["errors"] = response.data
        elif isinstance(response.data, list):
            custom_data["detail"] = response.data[0] if response.data else "An error occurred."
            custom_data["errors"] = response.data
        else:
            custom_data["detail"] = str(response.data)

        response.data = custom_data
        logger.warning(f"Handled API Exception: {exc.__class__.__name__} -> {response.status_code} in {context.get('view')}")
        return response

    # Unhandled 500 errors
    logger.error(f"Unhandled Server Exception: {str(exc)} in {context.get('view')}", exc_info=True)
    return Response(
        {
            "title": "InternalServerError",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "An internal server error occurred. Please contact the administrator.",
            "errors": None
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
