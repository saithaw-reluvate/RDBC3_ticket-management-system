import logging
import re

# Django's BaseHandler.get_response() unconditionally logs
# "%s: %s" % (reason_phrase, request.path) via the django.request logger for
# every 4xx/5xx response. Customer-plane URLs put the raw access token
# directly in the path (/api/track/<token>/...), so without this filter an
# invalid/expired/revoked/throttled lookup would write the raw token straight
# into logs/application.log — violating "never log raw ticket access tokens".
_TOKEN_PATH_RE = re.compile(r"(/api/track/)[^/]+")


class RedactTokenPathFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args and len(record.args) == 2:
            reason, path = record.args
            if isinstance(path, str) and "/api/track/" in path:
                record.args = (reason, _TOKEN_PATH_RE.sub(r"\1<redacted>", path))
        return True
