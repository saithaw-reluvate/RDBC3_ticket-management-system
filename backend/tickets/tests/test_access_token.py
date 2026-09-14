import hashlib

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from tickets.constants import IssuedFor
from tickets.models import TicketAccessToken

pytestmark = pytest.mark.django_db


def test_issue_creates_hashed_token_and_returns_raw(ticket):
    instance, raw_token = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)

    assert instance.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert instance.token_hash != raw_token
    assert instance.ticket_id == ticket.id


def test_is_valid_true_for_fresh_token(ticket):
    instance, _ = TicketAccessToken.issue(ticket)
    assert instance.is_valid is True


def test_is_valid_false_when_expired(ticket):
    instance, _ = TicketAccessToken.issue(ticket)
    # The DB constraint requires expires_at > created_at, so to simulate an
    # expired-but-internally-consistent row both timestamps move into the
    # past together in one UPDATE.
    TicketAccessToken.objects.filter(pk=instance.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=2),
        expires_at=timezone.now() - timezone.timedelta(days=1),
    )
    instance.refresh_from_db()
    assert instance.is_valid is False


def test_is_valid_false_when_revoked(ticket):
    instance, _ = TicketAccessToken.issue(ticket)
    instance.revoke()
    assert instance.is_valid is False
    assert instance.revoked_at is not None


def test_two_live_tokens_on_one_ticket_both_validate(ticket):
    first, first_raw = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
    second, second_raw = TicketAccessToken.issue(ticket, issued_for=IssuedFor.RESEND)

    assert first_raw != second_raw
    assert first.token_hash != second.token_hash
    assert first.is_valid is True
    assert second.is_valid is True
    assert ticket.access_tokens.count() == 2


def test_token_hash_unique_constraint(ticket):
    instance, _ = TicketAccessToken.issue(ticket)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TicketAccessToken.objects.create(
                ticket=ticket,
                token_hash=instance.token_hash,
                issued_for=IssuedFor.RESEND,
                expires_at=timezone.now() + timezone.timedelta(days=90),
            )


def test_expires_at_must_be_after_created_at(ticket):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TicketAccessToken.objects.create(
                ticket=ticket,
                token_hash="a" * 64,
                issued_for=IssuedFor.INITIAL,
                expires_at=timezone.now() - timezone.timedelta(days=1),
            )


def test_str_and_repr_do_not_expose_hash_or_raw_token(ticket):
    instance, raw_token = TicketAccessToken.issue(ticket)
    rendered = str(instance) + repr(instance)
    assert instance.token_hash not in rendered
    assert raw_token not in rendered
