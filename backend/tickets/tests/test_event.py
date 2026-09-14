import pytest

from tickets.constants import ActorType, CUSTOMER_VISIBLE_EVENT_TYPES, EventType
from tickets.models import TicketEvent

pytestmark = pytest.mark.django_db


def test_event_created(ticket):
    event = TicketEvent.objects.create(
        ticket=ticket, event_type=EventType.CREATED, actor_type=ActorType.CUSTOMER
    )
    assert event.pk is not None


def test_status_changed_event_records_old_and_new_value(ticket, staff_user):
    event = TicketEvent.objects.create(
        ticket=ticket,
        event_type=EventType.STATUS_CHANGED,
        actor=staff_user,
        actor_type=ActorType.ADMIN,
        old_value="OPEN",
        new_value="IN_PROGRESS",
    )
    assert event.old_value == "OPEN"
    assert event.new_value == "IN_PROGRESS"


def test_customer_visible_whitelist_contains_expected_codes():
    assert CUSTOMER_VISIBLE_EVENT_TYPES == {
        EventType.CREATED,
        EventType.STATUS_CHANGED,
        EventType.RESPONSE_ADDED,
    }


def test_operational_events_excluded_from_customer_whitelist():
    operational = {
        EventType.PRIORITY_CHANGED,
        EventType.ATTACHMENT_ADDED,
        EventType.TOKEN_ISSUED,
        EventType.TOKEN_REVOKED,
        EventType.EMAIL_SENT,
        EventType.EMAIL_FAILED,
    }
    assert operational.isdisjoint(CUSTOMER_VISIBLE_EVENT_TYPES)


def test_metadata_defaults_to_none(ticket):
    event = TicketEvent.objects.create(
        ticket=ticket, event_type=EventType.CREATED, actor_type=ActorType.SYSTEM
    )
    assert event.metadata is None
