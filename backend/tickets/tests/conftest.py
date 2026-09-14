import pytest
from django.contrib.auth import get_user_model

from tickets.constants import IssuedFor, Priority, Status
from tickets.models import Client, Ticket


@pytest.fixture
def ticket_client(db) -> Client:
    return Client.objects.create(email="Customer@Example.com")


@pytest.fixture
def ticket(db, ticket_client) -> Ticket:
    return Ticket.objects.create(
        client=ticket_client,
        reporter_name="Jane Customer",
        subject="Cannot access account",
        description="Login fails with a 500 error.",
        status=Status.OPEN,
        priority=Priority.MEDIUM,
    )


@pytest.fixture
def staff_user(db):
    User = get_user_model()
    return User.objects.create_user(username="admin1", password="not-a-real-password", is_staff=True)


@pytest.fixture
def issued_for():
    return IssuedFor.INITIAL
