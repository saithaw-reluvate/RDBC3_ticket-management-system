import re

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from tickets.constants import Priority, Status
from tickets.models import Response, Ticket, TicketAccessToken, TicketEvent

pytestmark = pytest.mark.django_db

REFERENCE_RE = re.compile(r"^TKT-[A-Z0-9]{8}$")


def test_reference_generated_on_create(ticket):
    assert REFERENCE_RE.match(ticket.reference)


def test_reference_unique(ticket_client):
    t1 = Ticket.objects.create(
        client=ticket_client, reporter_name="A", subject="s1", description="d1"
    )
    t2 = Ticket.objects.create(
        client=ticket_client, reporter_name="B", subject="s2", description="d2"
    )
    assert t1.reference != t2.reference


def test_default_status_and_priority(ticket):
    assert ticket.status == Status.OPEN
    assert ticket.priority == Priority.MEDIUM


def test_status_check_constraint_rejects_invalid_value(ticket_client):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Ticket.objects.create(
                client=ticket_client,
                reporter_name="A",
                subject="s",
                description="d",
                status="BOGUS",
            )


def test_priority_check_constraint_rejects_invalid_value(ticket_client):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Ticket.objects.create(
                client=ticket_client,
                reporter_name="A",
                subject="s",
                description="d",
                priority="URGENT",
            )


def test_resolved_at_required_when_status_resolved(ticket_client):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Ticket.objects.create(
                client=ticket_client,
                reporter_name="A",
                subject="s",
                description="d",
                status=Status.RESOLVED,
                resolved_at=None,
            )


def test_resolved_at_forbidden_when_status_not_resolved(ticket_client):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Ticket.objects.create(
                client=ticket_client,
                reporter_name="A",
                subject="s",
                description="d",
                status=Status.OPEN,
                resolved_at=timezone.now(),
            )


def test_resolved_at_consistency_allows_valid_combination(ticket_client):
    ticket = Ticket.objects.create(
        client=ticket_client,
        reporter_name="A",
        subject="s",
        description="d",
        status=Status.RESOLVED,
        resolved_at=timezone.now(),
    )
    assert ticket.pk is not None


def test_protect_blocks_deleting_client_with_tickets(ticket):
    with pytest.raises(ProtectedError):
        ticket.client.delete()


def test_cascade_deletes_ticket_children(ticket, staff_user):
    TicketAccessToken.issue(ticket)
    Response.objects.create(ticket=ticket, message="hello")
    TicketEvent.objects.create(ticket=ticket, event_type="CREATED", actor_type="system")

    ticket_id = ticket.id
    ticket.delete()

    assert not TicketAccessToken.objects.filter(ticket_id=ticket_id).exists()
    assert not Response.objects.filter(ticket_id=ticket_id).exists()
    assert not TicketEvent.objects.filter(ticket_id=ticket_id).exists()
