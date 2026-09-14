import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from tickets.constants import Category, IssuedFor, Priority, Status
from tickets.models import Response, Ticket, TicketAccessToken

pytestmark = pytest.mark.django_db


# --- auth ---------------------------------------------------------------


def test_login_success(api_client, staff_user):
    response = api_client.post(
        reverse("admin-login"), {"username": staff_user.username, "password": "not-a-real-password"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["is_staff"] is True


def test_login_wrong_password_rejected(api_client, staff_user):
    response = api_client.post(
        reverse("admin-login"), {"username": staff_user.username, "password": "wrong"}, format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_login_non_staff_user_rejected(api_client, db):
    from django.contrib.auth import get_user_model

    get_user_model().objects.create_user(username="regular", password="pw12345", is_staff=False)
    response = api_client.post(reverse("admin-login"), {"username": "regular", "password": "pw12345"}, format="json")
    assert response.status_code == 403


def test_me_unauthenticated_returns_403(api_client):
    response = api_client.get(reverse("admin-me"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_me_authenticated_returns_user(admin_api_client, staff_user):
    response = admin_api_client.get(reverse("admin-me"))
    assert response.status_code == 200
    assert response.json()["username"] == staff_user.username


def test_logout(admin_api_client):
    response = admin_api_client.post(reverse("admin-logout"))
    assert response.status_code == 204
    # session is gone: a subsequent admin call is rejected again
    assert admin_api_client.get(reverse("admin-me")).status_code == 403


def test_missing_csrf_token_rejected(staff_user, ticket):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(staff_user)
    response = client.patch(
        reverse("admin-ticket-detail", args=[ticket.reference]), {"priority": "HIGH"}, format="json"
    )
    assert response.status_code == 403


# --- list / detail --------------------------------------------------------


def test_list_unauthenticated_returns_403_not_404(api_client):
    response = api_client.get(reverse("admin-ticket-list"))
    assert response.status_code == 403


def test_list_returns_tickets(admin_api_client, ticket):
    response = admin_api_client.get(reverse("admin-ticket-list"))
    assert response.status_code == 200
    references = [t["reference"] for t in response.json()["results"]]
    assert ticket.reference in references


def test_list_filters_by_status(admin_api_client, ticket_client):
    open_ticket = Ticket.objects.create(
        client=ticket_client,
        reporter_name="A",
        subject="open one",
        description="d",
        category=Category.BUG,
        status=Status.OPEN,
    )
    resolved_ticket = Ticket.objects.create(
        client=ticket_client,
        reporter_name="A",
        subject="resolved one",
        description="d",
        category=Category.BUG,
        status=Status.RESOLVED,
        resolved_at="2026-01-01T00:00:00Z",
    )
    response = admin_api_client.get(reverse("admin-ticket-list"), {"status": "RESOLVED"})
    references = [t["reference"] for t in response.json()["results"]]
    assert resolved_ticket.reference in references
    assert open_ticket.reference not in references


def test_list_filters_by_category(admin_api_client, ticket_client):
    bug_ticket = Ticket.objects.create(
        client=ticket_client, reporter_name="A", subject="bug one", description="d", category=Category.BUG
    )
    billing_ticket = Ticket.objects.create(
        client=ticket_client, reporter_name="A", subject="billing one", description="d", category=Category.BILLING
    )
    response = admin_api_client.get(reverse("admin-ticket-list"), {"category": "BILLING"})
    references = [t["reference"] for t in response.json()["results"]]
    assert billing_ticket.reference in references
    assert bug_ticket.reference not in references


def test_list_search_by_reference(admin_api_client, ticket):
    response = admin_api_client.get(reverse("admin-ticket-list"), {"search": ticket.reference})
    references = [t["reference"] for t in response.json()["results"]]
    assert references == [ticket.reference]


def test_detail_keyed_on_reference_not_pk(admin_api_client, ticket):
    response = admin_api_client.get(reverse("admin-ticket-detail", args=[ticket.reference]))
    assert response.status_code == 200

    response_by_pk = admin_api_client.get(reverse("admin-ticket-detail", args=[str(ticket.pk)]))
    assert response_by_pk.status_code == 404


def test_detail_includes_internal_responses_and_all_events(admin_api_client, ticket, staff_user):
    Response.objects.create(ticket=ticket, author=staff_user, message="internal", is_internal=True)
    response = admin_api_client.get(reverse("admin-ticket-detail", args=[ticket.reference]))
    messages = [r["message"] for r in response.json()["responses"]]
    assert "internal" in messages


def test_detail_not_found_for_unknown_reference(admin_api_client):
    response = admin_api_client.get(reverse("admin-ticket-detail", args=["TKT-ZZZZZZZZ"]))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --- update -----------------------------------------------------------


def test_patch_status(admin_api_client, ticket):
    response = admin_api_client.patch(
        reverse("admin-ticket-detail", args=[ticket.reference]), {"status": "IN_PROGRESS"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"


def test_patch_priority(admin_api_client, ticket):
    response = admin_api_client.patch(
        reverse("admin-ticket-detail", args=[ticket.reference]), {"priority": "HIGH"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "HIGH"


def test_patch_category(admin_api_client, ticket):
    response = admin_api_client.patch(
        reverse("admin-ticket-detail", args=[ticket.reference]), {"category": "BILLING"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["category"] == "BILLING"


def test_patch_invalid_category_rejected(admin_api_client, ticket):
    response = admin_api_client.patch(
        reverse("admin-ticket-detail", args=[ticket.reference]), {"category": "FEATURE_REQUEST"}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_patch_invalid_status_rejected(admin_api_client, ticket):
    response = admin_api_client.patch(
        reverse("admin-ticket-detail", args=[ticket.reference]), {"status": "CLOSED"}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_patch_empty_body_rejected(admin_api_client, ticket):
    response = admin_api_client.patch(reverse("admin-ticket-detail", args=[ticket.reference]), {}, format="json")
    assert response.status_code == 400


# --- responses -----------------------------------------------------------


def test_add_response_public(admin_api_client, ticket):
    mail.outbox.clear()
    response = admin_api_client.post(
        reverse("admin-ticket-responses", args=[ticket.reference]),
        {"message": "We're on it.", "is_internal": False},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["is_internal"] is False
    assert len(mail.outbox) == 1


def test_add_response_internal(admin_api_client, ticket):
    mail.outbox.clear()
    response = admin_api_client.post(
        reverse("admin-ticket-responses", args=[ticket.reference]),
        {"message": "internal note", "is_internal": True},
        format="json",
    )
    assert response.status_code == 201
    assert len(mail.outbox) == 0


def test_add_response_unauthenticated_rejected(api_client, ticket):
    response = api_client.post(
        reverse("admin-ticket-responses", args=[ticket.reference]), {"message": "hi"}, format="json"
    )
    assert response.status_code == 403


# --- resend / revoke -----------------------------------------------------------


def test_admin_resend_link(admin_api_client, ticket):
    mail.outbox.clear()
    response = admin_api_client.post(reverse("admin-ticket-resend-link", args=[ticket.reference]))
    assert response.status_code == 200
    assert ticket.access_tokens.count() == 1
    assert len(mail.outbox) == 1


def test_admin_revoke_links(admin_api_client, ticket):
    TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    TicketAccessToken.issue(ticket, issued_for=IssuedFor.RESEND)

    response = admin_api_client.post(reverse("admin-ticket-revoke-links", args=[ticket.reference]))

    assert response.status_code == 200
    assert response.json()["revoked"] == 2


# --- attachments -----------------------------------------------------------


def test_admin_attachment_download(admin_api_client, ticket):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from tickets.models import Attachment

    attachment = Attachment.objects.create(
        ticket=ticket,
        file=SimpleUploadedFile("a.txt", b"hi", content_type="text/plain"),
        original_filename="a.txt",
        content_type="text/plain",
        size_bytes=2,
    )
    response = admin_api_client.get(
        reverse("admin-ticket-attachment", args=[ticket.reference, attachment.id])
    )
    assert response.status_code == 200
    assert response["X-Content-Type-Options"] == "nosniff"
    attachment.file.delete(save=False)


def test_admin_attachment_download_wrong_ticket_returns_404(admin_api_client, ticket, ticket_client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from tickets.models import Attachment

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
    response = admin_api_client.get(
        reverse("admin-ticket-attachment", args=[ticket.reference, other_attachment.id])
    )
    assert response.status_code == 404
    other_attachment.file.delete(save=False)
