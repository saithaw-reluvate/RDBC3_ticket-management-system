import logging

from django.db import transaction
from django.utils import timezone

from tickets.constants import ActorType, EventType, IssuedFor, Status
from tickets.models import Client, Response, Ticket
from tickets.services import attachments as attachments_service
from tickets.services import emails as emails_service
from tickets.services import events as events_service
from tickets.services import tokens as tokens_service

logger = logging.getLogger(__name__)


def create_ticket(
    *, reporter_name: str, email: str, subject: str, category: str, description: str, files=None
) -> Ticket:
    files = files or []
    # Validate before creating anything, so a bad upload never leaves a
    # half-created ticket behind.
    attachments_service.validate_files(files)

    with transaction.atomic():
        client, _ = Client.objects.get_or_create(email=email.strip().lower())
        ticket = Ticket.objects.create(
            client=client,
            reporter_name=reporter_name,
            subject=subject,
            category=category,
            description=description,
        )
        events_service.record(ticket, EventType.CREATED, actor_type=ActorType.CUSTOMER)

        for attachment in attachments_service.store_files(ticket, files):
            events_service.record(
                ticket,
                EventType.ATTACHMENT_ADDED,
                actor_type=ActorType.CUSTOMER,
                note=attachment.original_filename[:255],
            )

        _, raw_token = tokens_service.issue_token(ticket, issued_for=IssuedFor.INITIAL)
        events_service.record(ticket, EventType.TOKEN_ISSUED, actor_type=ActorType.SYSTEM)

    logger.info("Ticket created: ticket_id=%s reference=%s", ticket.id, ticket.reference)
    # Outside the transaction: no point holding the DB connection open for a
    # synchronous SMTP call, and a mail failure must never roll back the ticket.
    emails_service.send_ticket_created(ticket, raw_token)
    return ticket


def resend_links_for_email(email: str) -> None:
    normalized = email.strip().lower()
    for ticket in Ticket.objects.filter(client__email=normalized):
        _, raw_token = tokens_service.issue_token(ticket, issued_for=IssuedFor.RESEND)
        events_service.record(ticket, EventType.TOKEN_ISSUED, actor_type=ActorType.CUSTOMER)
        emails_service.send_link_resend(ticket, raw_token)


def update_status(ticket: Ticket, new_status: str, *, actor) -> Ticket:
    old_status = ticket.status
    if new_status == old_status:
        return ticket

    ticket.status = new_status
    ticket.resolved_at = timezone.now() if new_status == Status.RESOLVED else None
    ticket.save(update_fields=["status", "resolved_at", "updated_at"])

    events_service.record(
        ticket,
        EventType.STATUS_CHANGED,
        actor=actor,
        actor_type=ActorType.ADMIN,
        old_value=old_status,
        new_value=new_status,
    )

    _, raw_token = tokens_service.issue_token(ticket, issued_for=IssuedFor.STATUS_UPDATE)
    events_service.record(ticket, EventType.TOKEN_ISSUED, actor_type=ActorType.SYSTEM)
    emails_service.send_status_changed(ticket, raw_token, old_status, new_status)
    return ticket


def update_priority(ticket: Ticket, new_priority: str, *, actor) -> Ticket:
    old_priority = ticket.priority
    if new_priority == old_priority:
        return ticket

    ticket.priority = new_priority
    ticket.save(update_fields=["priority", "updated_at"])

    events_service.record(
        ticket,
        EventType.PRIORITY_CHANGED,
        actor=actor,
        actor_type=ActorType.ADMIN,
        old_value=old_priority,
        new_value=new_priority,
    )
    return ticket


def update_category(ticket: Ticket, new_category: str, *, actor) -> Ticket:
    old_category = ticket.category
    if new_category == old_category:
        return ticket

    ticket.category = new_category
    ticket.save(update_fields=["category", "updated_at"])

    events_service.record(
        ticket,
        EventType.CATEGORY_CHANGED,
        actor=actor,
        actor_type=ActorType.ADMIN,
        old_value=old_category,
        new_value=new_category,
    )
    return ticket


def add_response(ticket: Ticket, *, author, message: str, is_internal: bool) -> Response:
    response = Response.objects.create(ticket=ticket, author=author, message=message, is_internal=is_internal)
    events_service.record(
        ticket,
        EventType.RESPONSE_ADDED,
        actor=author,
        actor_type=ActorType.ADMIN,
        note="internal" if is_internal else None,
    )

    if not is_internal:
        _, raw_token = tokens_service.issue_token(ticket, issued_for=IssuedFor.STATUS_UPDATE)
        events_service.record(ticket, EventType.TOKEN_ISSUED, actor_type=ActorType.SYSTEM)
        emails_service.send_response_added(ticket, raw_token)

    return response
