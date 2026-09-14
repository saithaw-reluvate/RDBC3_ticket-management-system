from unittest.mock import patch

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_unhandled_exception_returns_uniform_500_envelope(api_client):
    with patch(
        "tickets.services.tickets.create_ticket", side_effect=RuntimeError("boom")
    ):
        response = api_client.post(
            reverse("ticket-create"),
            {"reporter_name": "A", "email": "a@example.com", "subject": "s", "category": "BUG", "description": "d"},
            format="multipart",
        )
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "server_error"
    assert "boom" not in body["error"]["message"]  # no stack trace/detail leaks to the client


def test_csrf_failure_view_returns_json_envelope():
    from tickets.exceptions import csrf_failure

    response = csrf_failure(None)
    assert response.status_code == 403
    import json

    body = json.loads(response.content)
    assert body["error"]["code"] == "permission_denied"


def test_invalid_token_lookup_does_not_leak_raw_token_into_logs(api_client):
    # Django's BaseHandler.get_response() logs request.path via the
    # django.request logger for every 4xx/5xx response, and the raw token
    # lives in that path — regression guard for the redaction filter in
    # tickets/logging_filters.py. django.request has propagate=False (its
    # own file handlers), so caplog (root-attached) never sees these records
    # — assert against the real handler output instead via a temporary
    # in-memory handler on that exact logger.
    import io
    import logging

    raw_token = "totally-fake-but-recognizable-raw-token-value"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    django_request_logger = logging.getLogger("django.request")
    django_request_logger.addHandler(handler)
    try:
        response = api_client.get(reverse("ticket-track", args=[raw_token]))
    finally:
        django_request_logger.removeHandler(handler)

    assert response.status_code == 404
    output = stream.getvalue()
    assert raw_token not in output
    assert "<redacted>" in output
