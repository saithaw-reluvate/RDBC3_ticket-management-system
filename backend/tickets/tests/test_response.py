import pytest

from tickets.models import Response

pytestmark = pytest.mark.django_db


def test_response_created(ticket, staff_user):
    response = Response.objects.create(ticket=ticket, author=staff_user, message="We're on it.")
    assert response.pk is not None
    assert response.is_internal is False


def test_response_is_internal_flag(ticket, staff_user):
    response = Response.objects.create(
        ticket=ticket, author=staff_user, message="Internal note", is_internal=True
    )
    assert response.is_internal is True


def test_author_set_null_when_user_deleted(ticket, staff_user):
    response = Response.objects.create(ticket=ticket, author=staff_user, message="hi")
    staff_user.delete()
    response.refresh_from_db()
    assert response.author_id is None
    assert response.pk is not None
