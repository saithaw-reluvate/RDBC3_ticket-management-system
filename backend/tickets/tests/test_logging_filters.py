import logging

from tickets.logging_filters import RedactTokenPathFilter


def _record(msg, args):
    return logging.LogRecord(
        name="test", level=logging.WARNING, pathname=__file__, lineno=1, msg=msg, args=args, exc_info=None
    )


def test_redacts_django_request_style_two_arg_path():
    # django.request: logger.warning("%s: %s", reason_phrase, request.path)
    record = _record("%s: %s", ("Not Found", "/api/track/SECRET_RAW_TOKEN/"))
    RedactTokenPathFilter().filter(record)
    assert record.getMessage() == "Not Found: /api/track/<redacted>/"
    assert "SECRET_RAW_TOKEN" not in record.getMessage()


def test_redacts_django_server_style_request_line_arg():
    # django.server: logger.info('"%s" %s %s', request_line, status, size) —
    # the dev server's WSGIRequestHandler.log_message().
    record = _record(
        '"%s" %s %s', ("GET /api/track/SECRET_RAW_TOKEN/attachments/4/ HTTP/1.1", "200", "83")
    )
    RedactTokenPathFilter().filter(record)
    assert "SECRET_RAW_TOKEN" not in record.getMessage()
    assert "/api/track/<redacted>/attachments/4/" in record.getMessage()


def test_leaves_unrelated_messages_untouched():
    record = _record("%s: %s", ("Not Found", "/api/admin/tickets/TKT-ABCDEFGH/"))
    RedactTokenPathFilter().filter(record)
    assert record.getMessage() == "Not Found: /api/admin/tickets/TKT-ABCDEFGH/"


def test_filter_always_returns_true():
    record = _record("no args here", None)
    assert RedactTokenPathFilter().filter(record) is True
