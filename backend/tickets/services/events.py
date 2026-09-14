import logging

from tickets.constants import ActorType
from tickets.models import Ticket, TicketEvent

logger = logging.getLogger(__name__)


def record(
    ticket: Ticket,
    event_type: str,
    *,
    actor=None,
    actor_type: str = ActorType.SYSTEM,
    old_value: str | None = None,
    new_value: str | None = None,
    note: str | None = None,
    metadata: dict | None = None,
) -> TicketEvent:
    """The single writer of ticket history. metadata is a small convenience
    column beside the structured fields — never a raw or hashed token."""
    event = TicketEvent.objects.create(
        ticket=ticket,
        event_type=event_type,
        actor=actor,
        actor_type=actor_type,
        old_value=old_value,
        new_value=new_value,
        note=note,
        metadata=metadata,
    )
    logger.info(
        "Ticket event recorded: ticket_id=%s event_type=%s actor_type=%s",
        ticket.id,
        event_type,
        actor_type,
    )
    return event
