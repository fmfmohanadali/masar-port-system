import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('core')


class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            duration_ms = int(duration * 1000)
            log_method = logger.warning if duration > 1.0 else logger.debug
            log_method(
                f"{request.method} {request.path} "
                f"-> {response.status_code} "
                f"({duration_ms}ms) "
                f"[{self._get_client_ip(request)}]"
            )
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
