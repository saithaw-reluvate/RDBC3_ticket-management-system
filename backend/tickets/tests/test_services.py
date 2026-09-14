from unittest.mock import patch

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from tickets.constants import ActorType, EventType, IssuedFor, Status
from tickets.exceptions import ExpiredTokenError, InvalidTokenError, RevokedTokenError
from tickets.models import Ticket, TicketAccessToken, TicketEvent
from tickets.services import attachments as attachments_service
from tickets.services import events as events_service
from tickets.services import tickets as tickets_service
from tickets.services import tokens as tokens_service

pytestmark = pytest.mark.django_db


# --- tokens.py ---------------------------------------------------------------


def test_resolve_token_returns_ticket_for_valid_token(ticket):
    _, raw_token = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    resolved = tokens_service.resolve_token(raw_token)
    assert resolved.id == ticket.id


def test_resolve_token_updates_last_used_at(ticket):
    instance, raw_token = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    assert instance.last_used_at is None
    tokens_service.resolve_token(raw_token)
    instance.refresh_from_db()
    assert instance.last_used_at is not None


def test_resolve_token_raises_invalid_for_unknown_token(ticket):
    with pytest.raises(InvalidTokenError):
        tokens_service.resolve_token("this-token-does-not-exist")


def test_resolve_token_raises_revoked(ticket):
    instance, raw_token = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    instance.revoke()
    with pytest.raises(RevokedTokenError):
        tokens_service.resolve_token(raw_token)


def test_resolve_token_raises_expired(ticket):
    from django.utils import timezone

    instance, raw_token = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    TicketAccessToken.objects.filter(pk=instance.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=2),
        expires_at=timezone.now() - timezone.timedelta(days=1),
    )
    with pytest.raises(ExpiredTokenError):
        tokens_service.resolve_token(raw_token)


def test_revoke_active_tokens_revokes_only_active_ones(ticket):
    first, _ = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    second, _ = TicketAccessToken.issue(ticket, issued_for=IssuedFor.RESEND)
    first.revoke()

    count = tokens_service.revoke_active_tokens(ticket)

    assert count == 1
    second.refresh_from_db()
    assert second.revoked_at is not None


# --- events.py ---------------------------------------------------------------


def test_record_creates_event(ticket):
    event = events_service.record(ticket, EventType.CREATED, actor_type=ActorType.CUSTOMER)
    assert event.pk is not None
    assert event.ticket_id == ticket.id


# --- attachments.py -----------------------------------------------------------


def _pdf(name="doc.pdf", size=100):
    return SimpleUploadedFile(name, b"x" * size, content_type="application/pdf")


def test_validate_files_rejects_disallowed_extension(settings):
    bad = SimpleUploadedFile("script.svg", b"<svg></svg>", content_type="image/svg+xml")
    with pytest.raises(ValidationError):
        attachments_service.validate_files([bad])


def test_validate_files_rejects_oversized_file(settings):
    settings.ATTACHMENT_MAX_BYTES = 10
    with pytest.raises(ValidationError):
        attachments_service.validate_files([_pdf(size=100)])


def test_validate_files_rejects_too_many_files(settings):
    settings.ATTACHMENT_MAX_COUNT = 2
    with pytest.raises(ValidationError):
        attachments_service.validate_files([_pdf("a.pdf"), _pdf("b.pdf"), _pdf("c.pdf")])


def test_validate_files_rejects_content_type_mismatch():
    mismatched = SimpleUploadedFile("fake.pdf", b"not really a pdf", content_type="text/html")
    with pytest.raises(ValidationError):
        attachments_service.validate_files([mismatched])


def test_validate_files_accepts_allowed_file():
    attachments_service.validate_files([_pdf()])  # should not raise


# --- tickets.py orchestration ---------------------------------------------------


def test_create_ticket_creates_client_ticket_event_token_and_sends_email():
    ticket = tickets_service.create_ticket(
        reporter_name="Jane",
        email="Jane@Example.com",
        subject="Help",
        description="Something is broken.",
    )

    assert ticket.client.email == "jane@example.com"
    assert ticket.access_tokens.count() == 1
    assert TicketEvent.objects.filter(ticket=ticket, event_type=EventType.CREATED).exists()
    assert TicketEvent.objects.filter(ticket=ticket, event_type=EventType.TOKEN_ISSUED).exists()
    assert len(mail.outbox) == 1
    assert "track" in mail.outbox[0].body


def test_create_ticket_reuses_existing_client():
    tickets_service.create_ticket(
        reporter_name="Jane", email="jane@example.com", subject="s1", description="d1"
    )
    ticket2 = tickets_service.create_ticket(
        reporter_name="Jane Again", email="jane@example.com", subject="s2", description="d2"
    )
    assert ticket2.client.tickets.count() == 2


def test_create_ticket_stores_attachments_and_records_events():
    ticket = tickets_service.create_ticket(
        reporter_name="Jane",
        email="jane@example.com",
        subject="Help",
        description="Broken",
        files=[_pdf("evidence.pdf")],
    )
    assert ticket.attachments.count() == 1
    assert TicketEvent.objects.filter(ticket=ticket, event_type=EventType.ATTACHMENT_ADDED).count() == 1


def test_create_ticket_rejects_invalid_attachment_without_creating_ticket():
    bad = SimpleUploadedFile("script.exe", b"MZ", content_type="application/octet-stream")
    with pytest.raises(ValidationError):
        tickets_service.create_ticket(
            reporter_name="Jane", email="jane@example.com", subject="s", description="d", files=[bad]
        )
    assert not Ticket.objects.exists()


def test_create_ticket_email_failure_is_logged_and_does_not_raise():
    with patch("tickets.services.emails.send_mail", side_effect=OSError("smtp down")):
        ticket = tickets_service.create_ticket(
            reporter_name="Jane", email="jane@example.com", subject="s", description="d"
        )
    assert ticket.pk is not None
    assert TicketEvent.objects.filter(ticket=ticket, event_type=EventType.EMAIL_FAILED).exists()


def test_resend_links_for_email_issues_fresh_token_per_ticket():
    t1 = tickets_service.create_ticket(reporter_name="A", email="dup@example.com", subject="s1", description="d1")
    t2 = tickets_service.create_ticket(reporter_name="A", email="dup@example.com", subject="s2", description="d2")
    mail.outbox.clear()

    tickets_service.resend_links_for_email("dup@example.com")

    t1.refresh_from_db()
    t2.refresh_from_db()
    assert t1.access_tokens.count() == 2
    assert t2.access_tokens.count() == 2
    assert len(mail.outbox) == 2


def test_resend_links_for_unknown_email_sends_nothing():
    tickets_service.resend_links_for_email("nobody@example.com")
    assert len(mail.outbox) == 0


def test_update_status_records_event_mints_token_and_emails(ticket, staff_user):
    mail.outbox.clear()
    updated = tickets_service.update_status(ticket, Status.IN_PROGRESS, actor=staff_user)

    assert updated.status == Status.IN_PROGRESS
    assert TicketEvent.objects.filter(
        ticket=ticket, event_type=EventType.STATUS_CHANGED, old_value=Status.OPEN, new_value=Status.IN_PROGRESS
    ).exists()
    assert ticket.access_tokens.count() == 1
    assert len(mail.outbox) == 1


def test_update_status_to_resolved_sets_resolved_at(ticket, staff_user):
    updated = tickets_service.update_status(ticket, Status.RESOLVED, actor=staff_user)
    assert updated.resolved_at is not None


def test_update_status_reopen_clears_resolved_at(ticket, staff_user):
    tickets_service.update_status(ticket, Status.RESOLVED, actor=staff_user)
    updated = tickets_service.update_status(ticket, Status.OPEN, actor=staff_user)
    assert updated.resolved_at is None


def test_update_status_noop_when_unchanged(ticket, staff_user):
    mail.outbox.clear()
    tickets_service.update_status(ticket, ticket.status, actor=staff_user)
    assert len(mail.outbox) == 0
    assert not TicketEvent.objects.filter(ticket=ticket, event_type=EventType.STATUS_CHANGED).exists()


def test_update_priority_records_event(ticket, staff_user):
    from tickets.constants import Priority

    updated = tickets_service.update_priority(ticket, Priority.HIGH, actor=staff_user)
    assert updated.priority == Priority.HIGH
    assert TicketEvent.objects.filter(ticket=ticket, event_type=EventType.PRIORITY_CHANGED).exists()


def test_add_response_public_sends_email_and_mints_token(ticket, staff_user):
    mail.outbox.clear()
    response = tickets_service.add_response(ticket, author=staff_user, message="We're on it.", is_internal=False)

    assert response.pk is not None
    assert len(mail.outbox) == 1
    assert ticket.access_tokens.count() == 1
    assert TicketEvent.objects.filter(ticket=ticket, event_type=EventType.RESPONSE_ADDED).exists()


def test_add_response_internal_does_not_send_email_or_mint_token(ticket, staff_user):
    mail.outbox.clear()
    tickets_service.add_response(ticket, author=staff_user, message="internal note", is_internal=True)

    assert len(mail.outbox) == 0
    assert ticket.access_tokens.count() == 0
