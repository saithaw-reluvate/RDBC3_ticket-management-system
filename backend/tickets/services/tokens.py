import hashlib
import logging

from django.conf import settings
from django.utils import timezone

from tickets.exceptions import ExpiredTokenError, InvalidTokenError, RevokedTokenError
from tickets.models import Ticket, TicketAccessToken

logger = logging.getLogger(__name__)


def issue_token(ticket: Ticket, issued_for: str) -> tuple[TicketAccessToken, str]:
    return TicketAccessToken.issue(ticket, issued_for=issued_for, ttl_days=settings.TICKET_TOKEN_TTL_DAYS)


def resolve_token(raw_token: str) -> Ticket:
    """Single entry point for the customer plane. Hashes the presented
    value, looks it up by token_hash, checks validity, and updates
    last_used_at. Never logs, returns, or embeds the raw token."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    try:
        instance = TicketAccessToken.objects.select_related("ticket").get(token_hash=token_hash)
    except TicketAccessToken.DoesNotExist:
        logger.warning("Token lookup failed: no matching token")
        raise InvalidTokenError()

    if instance.revoked_at is not None:
        logger.warning("Token lookup failed: revoked (ticket_id=%s)", instance.ticket_id)
        raise RevokedTokenError()

    if instance.expires_at <= timezone.now():
        logger.warning("Token lookup failed: expired (ticket_id=%s)", instance.ticket_id)
        raise ExpiredTokenError()

    instance.last_used_at = timezone.now()
    instance.save(update_fields=["last_used_at"])
    return instance.ticket


def revoke_active_tokens(ticket: Ticket) -> int:
    now = timezone.now()
    count = TicketAccessToken.objects.filter(ticket=ticket, revoked_at__isnull=True).update(revoked_at=now)
    logger.info("Tokens revoked: ticket_id=%s count=%s", ticket.id, count)
    return count
