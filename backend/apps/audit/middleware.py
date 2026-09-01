class AuditLoggingMiddleware:
    """
    Middleware that captures client IP address on incoming requests
    and attaches it to the request object for easy logging.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        request.client_ip = ip

        response = self.get_response(request)
        return response
