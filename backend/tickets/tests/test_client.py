import pytest
from django.db import IntegrityError, transaction

from tickets.models import Client

pytestmark = pytest.mark.django_db


def test_email_normalized_to_lowercase_on_save():
    client = Client.objects.create(email="Mixed.Case@Example.COM")
    client.refresh_from_db()
    assert client.email == "mixed.case@example.com"


def test_email_uniqueness_collision():
    Client.objects.create(email="dup@example.com")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Client.objects.create(email="DUP@example.com")
