from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.constants import ActorType, Category, EventType, IssuedFor, Priority, Status
from tickets.models import Client, Response, Ticket, TicketAccessToken, TicketEvent


class Command(BaseCommand):
    help = "Seed a small set of demo tickets for manual QA of the schema."

    def handle(self, *args, **options):
        client, _ = Client.objects.get_or_create(email="demo.customer@example.com")

        ticket, created = Ticket.objects.get_or_create(
            client=client,
            subject="Cannot log in to portal",
            defaults={
                "reporter_name": "Demo Customer",
                "description": "Getting an error when trying to sign in since this morning.",
                "category": Category.ACCOUNT_ACCESS,
                "status": Status.OPEN,
                "priority": Priority.HIGH,
            },
        )

        if created:
            TicketEvent.objects.create(
                ticket=ticket,
                event_type=EventType.CREATED,
                actor_type=ActorType.CUSTOMER,
            )
            token, raw_token = TicketAccessToken.issue(ticket, issued_for=IssuedFor.INITIAL)
            TicketEvent.objects.create(
                ticket=ticket,
                event_type=EventType.TOKEN_ISSUED,
                actor_type=ActorType.SYSTEM,
            )
            Response.objects.create(
                ticket=ticket,
                message="Thanks for reaching out, we're looking into this.",
                is_internal=False,
            )
            TicketEvent.objects.create(
                ticket=ticket,
                event_type=EventType.RESPONSE_ADDED,
                actor_type=ActorType.ADMIN,
            )
            self.stdout.write(self.style.SUCCESS(f"Created demo ticket {ticket.reference}"))
            self.stdout.write(f"Demo tracking token (dev only, not stored): {raw_token}")
        else:
            self.stdout.write(self.style.WARNING(f"Demo ticket already exists: {ticket.reference}"))
