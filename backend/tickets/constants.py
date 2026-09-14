"""
Status/priority/event-type choices and the customer-visible event whitelist.
One source of truth, per docs/DATABASE.md Decision 9.
"""

from django.db import models


class Status(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED = "RESOLVED", "Resolved"


class Priority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class Category(models.TextChoices):
    """The seven approved values, per docs/DATABASE.md §2 Decision 13 —
    that table is the source of truth for this list."""

    ACCOUNT_ACCESS = "ACCOUNT_ACCESS", "Login & account access"
    BILLING = "BILLING", "Billing & payments"
    BUG = "BUG", "Something is broken"
    PERFORMANCE = "PERFORMANCE", "Slow or unavailable"
    DATA = "DATA", "Incorrect or missing data"
    SECURITY = "SECURITY", "Security concern"
    OTHER = "OTHER", "Something else"


class IssuedFor(models.TextChoices):
    INITIAL = "initial", "Initial"
    STATUS_UPDATE = "status_update", "Status update"
    RESEND = "resend", "Resend"


class ActorType(models.TextChoices):
    SYSTEM = "system", "System"
    CUSTOMER = "customer", "Customer"
    ADMIN = "admin", "Admin"


class EventType(models.TextChoices):
    CREATED = "CREATED", "Created"
    STATUS_CHANGED = "STATUS_CHANGED", "Status changed"
    PRIORITY_CHANGED = "PRIORITY_CHANGED", "Priority changed"
    CATEGORY_CHANGED = "CATEGORY_CHANGED", "Category changed"
    RESPONSE_ADDED = "RESPONSE_ADDED", "Response added"
    ATTACHMENT_ADDED = "ATTACHMENT_ADDED", "Attachment added"
    TOKEN_ISSUED = "TOKEN_ISSUED", "Token issued"
    TOKEN_REVOKED = "TOKEN_REVOKED", "Token revoked"
    EMAIL_SENT = "EMAIL_SENT", "Email sent"
    EMAIL_FAILED = "EMAIL_FAILED", "Email failed"


# Events a customer is allowed to see on their own ticket's timeline. This is
# the whitelist itself (Decision 9) — filtering happens against this
# constant, not a database column.
CUSTOMER_VISIBLE_EVENT_TYPES = frozenset(
    {
        EventType.CREATED,
        EventType.STATUS_CHANGED,
        EventType.RESPONSE_ADDED,
    }
)

TOKEN_TTL_DAYS = 90
