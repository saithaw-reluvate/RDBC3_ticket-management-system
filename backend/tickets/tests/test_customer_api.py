import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from tickets.constants import ActorType, Category, EventType, IssuedFor
from tickets.models import Attachment, Response, Ticket, TicketAccessToken
from tickets.services import events as events_service

pytestmark = pytest.mark.django_db


def _issue(ticket):
    _, raw = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    return raw


def test_track_valid_token_returns_ticket(api_client, ticket):
    raw = _issue(ticket)
    events_service.record(ticket, EventType.CREATED, actor_type=ActorType.CUSTOMER)

    response = api_client.get(reverse("ticket-track", args=[raw]))

    assert response.status_code == 200
    data = response.json()
    assert data["reference"] == ticket.reference
    assert data["subject"] == ticket.subject
    assert data["category"] == Category.ACCOUNT_ACCESS
    assert data["category_display"] == "Login & account access"


def test_track_invalid_token_returns_404_envelope(api_client):
    response = api_client.get(reverse("ticket-track", args=["not-a-real-token"]))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "invalid_token"


def test_track_succeeds_with_existing_admin_session(staff_user, ticket):
    # Customer plane identity comes solely from the URL token — see the
    # matching regression tests in test_public_api.py. An active admin
    # session must never affect this endpoint's behaviour.
    raw = _issue(ticket)
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(staff_user)

    response = client.get(reverse("ticket-track", args=[raw]))

    assert response.status_code == 200
    assert response.json()["reference"] == ticket.reference


def test_track_expired_token_returns_410(api_client, ticket):
    from django.utils import timezone

    instance, raw = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    TicketAccessToken.objects.filter(pk=instance.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=2),
        expires_at=timezone.now() - timezone.timedelta(days=1),
    )
    response = api_client.get(reverse("ticket-track", args=[raw]))
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "expired_token"


def test_track_revoked_token_returns_410(api_client, ticket):
    instance, raw = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    instance.revoke()
    response = api_client.get(reverse("ticket-track", args=[raw]))
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "revoked_token"


def test_token_for_ticket_a_cannot_read_ticket_b(api_client, ticket, ticket_client):
    other_ticket = Ticket.objects.create(
        client=ticket_client,
        reporter_name="Other",
        subject="Other subject",
        description="d",
        category=Category.BUG,
    )
    raw_for_a = _issue(ticket)

    response = api_client.get(reverse("ticket-track", args=[raw_for_a]))

    assert response.status_code == 200
    assert response.json()["reference"] == ticket.reference
    assert response.json()["reference"] != other_ticket.reference


def test_track_filters_internal_responses(api_client, ticket, staff_user):
    raw = _issue(ticket)
    Response.objects.create(ticket=ticket, author=staff_user, message="Public reply", is_internal=False)
    Response.objects.create(ticket=ticket, author=staff_user, message="Internal note", is_internal=True)

    response = api_client.get(reverse("ticket-track", args=[raw]))

    messages = [r["message"] for r in response.json()["responses"]]
    assert "Public reply" in messages
    assert "Internal note" not in messages


def test_track_filters_operational_events(api_client, ticket):
    raw = _issue(ticket)
    events_service.record(ticket, EventType.CREATED, actor_type=ActorType.CUSTOMER)
    events_service.record(ticket, EventType.TOKEN_ISSUED, actor_type=ActorType.SYSTEM)
    events_service.record(ticket, EventType.EMAIL_SENT, actor_type=ActorType.SYSTEM)

    response = api_client.get(reverse("ticket-track", args=[raw]))

    event_types = {e["event_type"] for e in response.json()["events"]}
    assert event_types == {"CREATED"}


def test_track_does_not_expose_response_author(api_client, ticket, staff_user):
    raw = _issue(ticket)
    Response.objects.create(ticket=ticket, author=staff_user, message="hi", is_internal=False)

    response = api_client.get(reverse("ticket-track", args=[raw]))

    assert "author" not in response.json()["responses"][0]


def test_track_throttled_after_limit(api_client, ticket, monkeypatch):
    from tickets.throttles import TokenLookupThrottle

    monkeypatch.setattr(TokenLookupThrottle, "THROTTLE_RATES", {"token_lookup": "2/hour"})
    raw = _issue(ticket)
    for _ in range(2):
        assert api_client.get(reverse("ticket-track", args=[raw])).status_code == 200

    response = api_client.get(reverse("ticket-track", args=[raw]))
    assert response.status_code == 429


def test_attachment_download_success(api_client, ticket):
    raw = _issue(ticket)
    attachment = Attachment.objects.create(
        ticket=ticket,
        file=SimpleUploadedFile("a.txt", b"hello", content_type="text/plain"),
        original_filename="a.txt",
        content_type="text/plain",
        size_bytes=5,
    )

    response = api_client.get(reverse("ticket-track-attachment", args=[raw, attachment.id]))

    assert response.status_code == 200
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Disposition"].startswith("attachment")
    attachment.file.delete(save=False)


def test_attachment_download_rejects_id_from_another_ticket(api_client, ticket, ticket_client):
    other_ticket = Ticket.objects.create(
        client=ticket_client, reporter_name="Other", subject="s", description="d", category=Category.BUG
    )
    other_attachment = Attachment.objects.create(
        ticket=other_ticket,
        file=SimpleUploadedFile("b.txt", b"x", content_type="text/plain"),
        original_filename="b.txt",
        content_type="text/plain",
        size_bytes=1,
    )
    raw_for_ticket = _issue(ticket)

    response = api_client.get(reverse("ticket-track-attachment", args=[raw_for_ticket, other_attachment.id]))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    other_attachment.file.delete(save=False)
