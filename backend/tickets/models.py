import hashlib
import logging
import secrets
import string
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .constants import ActorType, Category, EventType, IssuedFor, Priority, Status, TOKEN_TTL_DAYS

logger = logging.getLogger(__name__)

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
REFERENCE_LENGTH = 8
REFERENCE_MAX_ATTEMPTS = 10


def generate_reference() -> str:
    suffix = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(REFERENCE_LENGTH))
    return f"TKT-{suffix}"


def attachment_upload_path(instance: "Attachment", filename: str) -> str:
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-") or "file"
    return f"attachments/{uuid.uuid4().hex}/{uuid.uuid4().hex[:8]}-{safe_name}"


class Client(models.Model):
    """Identity-only record for a reporter, keyed by email. Never a Django
    user — customers never log in."""

    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email"]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email


class Ticket(models.Model):
    reference = models.CharField(max_length=16, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="tickets")
    reporter_name = models.CharField(max_length=150)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="ticket_status_created_idx"),
            models.Index(fields=["priority"], name="ticket_priority_idx"),
            models.Index(fields=["category"], name="ticket_category_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                name="ticket_status_valid",
                condition=Q(status__in=Status.values),
            ),
            models.CheckConstraint(
                name="ticket_priority_valid",
                condition=Q(priority__in=Priority.values),
            ),
            models.CheckConstraint(
                name="ticket_category_valid",
                condition=Q(category__in=Category.values),
            ),
            models.CheckConstraint(
                name="ticket_resolved_at_consistency",
                condition=(
                    Q(status=Status.RESOLVED, resolved_at__isnull=False)
                    | (~Q(status=Status.RESOLVED) & Q(resolved_at__isnull=True))
                ),
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_unique_reference()
        super().save(*args, **kwargs)

    def _generate_unique_reference(self) -> str:
        for _ in range(REFERENCE_MAX_ATTEMPTS):
            candidate = generate_reference()
            if not Ticket.objects.filter(reference=candidate).exists():
                return candidate
        raise RuntimeError("Could not generate a unique ticket reference")

    def __str__(self) -> str:
        return self.reference


class TicketAccessToken(models.Model):
    """Hashed customer-plane access token. Multiple may be live per ticket
    (Step 0 Decision 1) because a hash cannot be reversed to rebuild a link."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="access_tokens")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    issued_for = models.CharField(max_length=20, choices=IssuedFor.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="token_expires_after_created",
                condition=Q(expires_at__gt=models.F("created_at")),
            ),
        ]

    @classmethod
    def issue(
        cls,
        ticket: Ticket,
        issued_for: str = IssuedFor.INITIAL,
        ttl_days: int = TOKEN_TTL_DAYS,
    ) -> tuple["TicketAccessToken", str]:
        """Create a new token and return (instance, raw_token). The raw
        token exists only in memory here, long enough to build the email
        link — it is never persisted or logged."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        instance = cls.objects.create(
            ticket=ticket,
            token_hash=token_hash,
            issued_for=issued_for,
            expires_at=timezone.now() + timezone.timedelta(days=ttl_days),
        )
        logger.info(
            "Access token issued: ticket_id=%s issued_for=%s expires_at=%s",
            ticket.id,
            issued_for,
            instance.expires_at.isoformat(),
        )
        return instance, raw_token

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    def __str__(self) -> str:
        return f"TicketAccessToken(id={self.pk}, ticket_id={self.ticket_id}, issued_for={self.issued_for})"

    def __repr__(self) -> str:
        return self.__str__()


class Response(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="responses")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_responses",
    )
    message = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ticket", "created_at"], name="response_ticket_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Response(id={self.pk}, ticket_id={self.ticket_id})"


class TicketEvent(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_events",
    )
    actor_type = models.CharField(max_length=10, choices=ActorType.choices)
    old_value = models.CharField(max_length=50, null=True, blank=True)
    new_value = models.CharField(max_length=50, null=True, blank=True)
    note = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ticket", "created_at"], name="event_ticket_created_idx"),
        ]

    def __str__(self) -> str:
        return f"TicketEvent(id={self.pk}, ticket_id={self.ticket_id}, event_type={self.event_type})"


class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_upload_path)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(name="attachment_size_positive", condition=Q(size_bytes__gt=0)),
        ]

    def __str__(self) -> str:
        return f"Attachment(id={self.pk}, ticket_id={self.ticket_id}, filename={self.original_filename})"
