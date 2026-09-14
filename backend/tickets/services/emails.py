import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from tickets.constants import EventType
from tickets.models import Ticket
from tickets.services import events as events_service

logger = logging.getLogger(__name__)


def _tracking_url(raw_token: str) -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return f"{base}/track/{raw_token}/"


def _send(ticket: Ticket, subject: str, template_name: str, context: dict) -> None:
    """Synchronous, inside the request. A failure is logged and recorded as
    an EMAIL_FAILED event but never raises — ticket creation/updates must
    never fail because of mail delivery."""
    body = render_to_string(template_name, context)
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[ticket.client.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send email: ticket_id=%s subject=%r", ticket.id, subject)
        events_service.record(ticket, EventType.EMAIL_FAILED, note=subject[:255])
        return
    logger.info("Email sent: ticket_id=%s subject=%r", ticket.id, subject)
    events_service.record(ticket, EventType.EMAIL_SENT, note=subject[:255])


def send_ticket_created(ticket: Ticket, raw_token: str) -> None:
    _send(
        ticket,
        subject=f"[{ticket.reference}] We received your ticket",
        template_name="email/ticket_created.txt",
        context={"ticket": ticket, "tracking_url": _tracking_url(raw_token)},
    )


def send_status_changed(ticket: Ticket, raw_token: str, old_status: str, new_status: str) -> None:
    _send(
        ticket,
        subject=f"[{ticket.reference}] Status updated to {ticket.get_status_display()}",
        template_name="email/status_changed.txt",
        context={
            "ticket": ticket,
            "tracking_url": _tracking_url(raw_token),
            "old_status": old_status,
            "new_status": new_status,
        },
    )


def send_response_added(ticket: Ticket, raw_token: str) -> None:
    _send(
        ticket,
        subject=f"[{ticket.reference}] New response to your ticket",
        template_name="email/response_added.txt",
        context={"ticket": ticket, "tracking_url": _tracking_url(raw_token)},
    )


def send_link_resend(ticket: Ticket, raw_token: str) -> None:
    _send(
        ticket,
        subject=f"[{ticket.reference}] Your tracking link",
        template_name="email/link_resend.txt",
        context={"ticket": ticket, "tracking_url": _tracking_url(raw_token)},
    )
