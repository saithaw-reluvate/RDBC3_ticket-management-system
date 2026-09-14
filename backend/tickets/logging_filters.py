import logging
import re

# Two Django loggers embed the raw request path in their log args, and
# customer-plane URLs put the raw access token directly in that path
# (/api/track/<token>/...):
#   - django.request: BaseHandler.get_response() logs
#     "%s: %s" % (reason_phrase, request.path) for every 4xx/5xx response.
#   - django.server: the dev server's WSGIRequestHandler.log_message() logs
#     the full request line ("GET /api/track/<token>/ HTTP/1.1", status, size).
# Without this filter, an invalid/expired/revoked/throttled lookup would
# write the raw token straight into logs/application.log — violating "never
# log raw ticket access tokens". Scans every string arg rather than assuming
# a fixed position/arity so it covers both log call shapes.
_TOKEN_PATH_RE = re.compile(r"(/api/track/)[^/\s\"]+")


class RedactTokenPathFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = tuple(
                _TOKEN_PATH_RE.sub(r"\1<redacted>", arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True
