import logging
import time

logger = logging.getLogger('api.request')


class RequestLogMiddleware:
    """Log method, path, status and duration for every request.

    ponytail: a few lines of structured logging covers observability now;
    reach for OpenTelemetry/metrics only when logs stop answering the question.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            '%s %s -> %s %.1fms',
            request.method, request.get_full_path(), response.status_code, duration_ms,
        )
        return response
