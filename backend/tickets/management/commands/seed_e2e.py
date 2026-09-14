import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.constants import ActorType, Category, EventType, IssuedFor
from tickets.models import Client, Ticket, TicketAccessToken, TicketEvent

E2E_ADMIN_USERNAME = "e2e_admin"
E2E_CLIENT_EMAIL = "e2e.fixtures@example.com"


class Command(BaseCommand):
    """Idempotent fixture setup for the Playwright E2E suite (Step 4).

    Run once via global-setup before the suite. Prints one line of JSON to
    stdout (app logs go to stderr, per LOGGING config, so this stays clean)
    with the data specs can't otherwise discover: the admin password used,
    and a pre-expired token that can only be produced by direct DB
    manipulation, never through the API — mirroring the same technique
    pytest and the Step 3 manual QA already use for this exact case.

    Does NOT create a general-purpose "ticket to manage" fixture — the E2E
    suite's main journey creates that itself through the real public
    submission form, so the full flow is exercised end-to-end rather than
    seeded around.
    """

    help = "Seed deterministic fixtures for the Playwright E2E suite."

    def add_arguments(self, parser):
        parser.add_argument("--admin-password", required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        admin, _ = User.objects.get_or_create(username=E2E_ADMIN_USERNAME, defaults={"is_staff": True})
        admin.is_staff = True
        admin.set_password(options["admin_password"])
        admin.save()

        Ticket.objects.filter(client__email=E2E_CLIENT_EMAIL).delete()
        Client.objects.filter(email=E2E_CLIENT_EMAIL).delete()
        client = Client.objects.create(email=E2E_CLIENT_EMAIL)

        expired_ticket = Ticket.objects.create(
            client=client,
            reporter_name="E2E Expired Fixture",
            subject="Expired token fixture",
            description="Seeded for the expired-token E2E test.",
            category=Category.OTHER,
        )
        TicketEvent.objects.create(ticket=expired_ticket, event_type=EventType.CREATED, actor_type=ActorType.CUSTOMER)
        token, raw_token = TicketAccessToken.issue(expired_ticket, issued_for=IssuedFor.INITIAL)
        TicketAccessToken.objects.filter(pk=token.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=100),
            expires_at=timezone.now() - timezone.timedelta(days=10),
        )

        self.stdout.write(
            json.dumps(
                {
                    "adminUsername": E2E_ADMIN_USERNAME,
                    "clientEmail": E2E_CLIENT_EMAIL,
                    "expiredTicketReference": expired_ticket.reference,
                    "expiredToken": raw_token,
                }
            )
        )
