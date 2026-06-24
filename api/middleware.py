import logging
import time

logger = logging.getLogger('api.request')


class RequestLogMiddleware:
    """Loga método, rota, status e duração de cada request.

    ponytail: poucas linhas de log estruturado cobrem a observabilidade agora;
    partir para OpenTelemetry/métricas só quando o log deixar de responder.
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
