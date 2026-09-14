import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from tickets.models import Ticket

pytestmark = pytest.mark.django_db


def test_submit_ticket_success(api_client):
    url = reverse("ticket-create")
    payload = {
        "reporter_name": "Jane Customer",
        "email": "jane@example.com",
        "subject": "Cannot log in",
        "category": "ACCOUNT_ACCESS",
        "description": "Getting a 500 error since this morning.",
    }
    response = api_client.post(url, payload, format="multipart")

    assert response.status_code == 201
    data = response.json()
    assert data["reference"].startswith("TKT-")
    assert data["category"] == "ACCOUNT_ACCESS"
    assert data["status"] == "OPEN"
    assert data["priority"] == "MEDIUM"
    # Decision 1: never return the tracking link/token in the response.
    assert "token" not in data
    assert len(mail.outbox) == 1


def test_submit_ticket_with_attachment(api_client):
    url = reverse("ticket-create")
    payload = {
        "reporter_name": "Jane",
        "email": "jane@example.com",
        "subject": "Broken",
        "category": "BUG",
        "description": "See attached.",
        "attachments": SimpleUploadedFile("evidence.png", b"\x89PNG\r\n", content_type="image/png"),
    }
    response = api_client.post(url, payload, format="multipart")

    assert response.status_code == 201
    ticket = Ticket.objects.get(reference=response.json()["reference"])
    assert ticket.attachments.count() == 1


def test_submit_ticket_rejects_disallowed_attachment_type(api_client):
    url = reverse("ticket-create")
    payload = {
        "reporter_name": "Jane",
        "email": "jane@example.com",
        "subject": "Broken",
        "category": "BUG",
        "description": "See attached.",
        "attachments": SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream"),
    }
    response = api_client.post(url, payload, format="multipart")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert not Ticket.objects.exists()


def test_submit_ticket_missing_required_field(api_client):
    url = reverse("ticket-create")
    payload = {"reporter_name": "Jane", "subject": "s", "category": "BUG", "description": "d"}  # no email
    response = api_client.post(url, payload, format="multipart")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "email" in body["error"]["details"]


def test_submit_ticket_missing_category(api_client):
    url = reverse("ticket-create")
    payload = {"reporter_name": "Jane", "email": "jane@example.com", "subject": "s", "description": "d"}
    response = api_client.post(url, payload, format="multipart")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "category" in body["error"]["details"]


def test_submit_ticket_invalid_category_rejected(api_client):
    url = reverse("ticket-create")
    payload = {
        "reporter_name": "Jane",
        "email": "jane@example.com",
        "subject": "s",
        "category": "FEATURE_REQUEST",
        "description": "d",
    }
    response = api_client.post(url, payload, format="multipart")

    assert response.status_code == 400
    assert "category" in response.json()["error"]["details"]


def test_submit_ticket_invalid_email(api_client):
    url = reverse("ticket-create")
    payload = {
        "reporter_name": "Jane",
        "email": "not-an-email",
        "subject": "s",
        "category": "BUG",
        "description": "d",
    }
    response = api_client.post(url, payload, format="multipart")
    assert response.status_code == 400


def test_submit_ticket_throttled_after_limit(api_client, monkeypatch):
    # DRF snapshots THROTTLE_RATES from settings at class-definition/import
    # time, so overriding settings.REST_FRAMEWORK mid-test has no effect —
    # patch the throttle class's rate table directly instead.
    from tickets.throttles import TicketCreateThrottle

    monkeypatch.setattr(TicketCreateThrottle, "THROTTLE_RATES", {"ticket_create": "2/hour"})
    url = reverse("ticket-create")
    payload = {
        "reporter_name": "Jane",
        "email": "jane@example.com",
        "subject": "s",
        "category": "BUG",
        "description": "d",
    }

    for _ in range(2):
        assert api_client.post(url, payload, format="multipart").status_code == 201

    response = api_client.post(url, payload, format="multipart")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "throttled"


def test_resend_link_constant_response_for_known_email(api_client, ticket):
    from tickets.models import TicketAccessToken

    TicketAccessToken.issue(ticket, issued_for="initial")
    mail.outbox.clear()

    url = reverse("ticket-resend-link")
    response = api_client.post(url, {"email": ticket.client.email}, format="json")

    assert response.status_code == 202
    assert len(mail.outbox) == 1


def test_resend_link_constant_response_for_unknown_email(api_client):
    url = reverse("ticket-resend-link")
    known_response = api_client.post(url, {"email": "known@example.com"}, format="json")
    unknown_response = api_client.post(url, {"email": "totally-unknown@example.com"}, format="json")

    assert known_response.status_code == unknown_response.status_code == 202
    assert known_response.json() == unknown_response.json()


def test_resend_link_throttled_after_limit(api_client):
    url = reverse("ticket-resend-link")
    for _ in range(3):
        assert api_client.post(url, {"email": "x@example.com"}, format="json").status_code == 202

    response = api_client.post(url, {"email": "x@example.com"}, format="json")
    assert response.status_code == 429


# --- public endpoints stay anonymous regardless of an existing admin session ---
#
# Regression for a real bug: DRF's SessionAuthentication enforces CSRF for any
# request that resolves to an *active* session user, independent of the view's
# permission_classes. With the global default authentication classes, a browser
# holding an unrelated admin session cookie got a CSRF 403 submitting a ticket —
# it worked in a private window only because no session cookie was sent at all.
# These use enforce_csrf_checks=True (matching test_admin_api.py's CSRF test) and
# deliberately send no CSRF token, so a regression here reproduces the bug as a 403.


def test_submit_ticket_succeeds_with_existing_admin_session(staff_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(staff_user)

    url = reverse("ticket-create")
    payload = {
        "reporter_name": "Jane Customer",
        "email": "jane@example.com",
        "subject": "Cannot log in",
        "category": "ACCOUNT_ACCESS",
        "description": "Getting a 500 error since this morning.",
    }
    response = client.post(url, payload, format="multipart")

    assert response.status_code == 201
    assert response.json()["reference"].startswith("TKT-")


def test_resend_link_succeeds_with_existing_admin_session(staff_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(staff_user)

    url = reverse("ticket-resend-link")
    response = client.post(url, {"email": "someone@example.com"}, format="json")

    assert response.status_code == 202
