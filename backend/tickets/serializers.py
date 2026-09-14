from rest_framework import serializers

from tickets.constants import CUSTOMER_VISIBLE_EVENT_TYPES, Priority, Status
from tickets.models import Attachment, Response, Ticket, TicketEvent

# --- Public plane -----------------------------------------------------------


class TicketCreateSerializer(serializers.Serializer):
    reporter_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    description = serializers.CharField()


class TicketCreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["reference", "subject", "status", "priority", "created_at"]


class ResendLinkSerializer(serializers.Serializer):
    email = serializers.EmailField()


# --- Customer plane -----------------------------------------------------------


class ResponseCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ["message", "created_at"]


class EventCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketEvent
        fields = ["event_type", "old_value", "new_value", "created_at"]


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["id", "original_filename", "size_bytes", "content_type"]


class TicketCustomerDetailSerializer(serializers.ModelSerializer):
    responses = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "reference",
            "subject",
            "description",
            "reporter_name",
            "status",
            "priority",
            "created_at",
            "resolved_at",
            "responses",
            "events",
            "attachments",
        ]

    def get_responses(self, ticket: Ticket):
        qs = ticket.responses.filter(is_internal=False)
        return ResponseCustomerSerializer(qs, many=True).data

    def get_events(self, ticket: Ticket):
        qs = ticket.events.filter(event_type__in=CUSTOMER_VISIBLE_EVENT_TYPES)
        return EventCustomerSerializer(qs, many=True).data


# --- Admin plane -----------------------------------------------------------


class ResponseAdminSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", default=None, read_only=True)

    class Meta:
        model = Response
        fields = ["id", "author", "message", "is_internal", "created_at"]


class EventAdminSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.username", default=None, read_only=True)

    class Meta:
        model = TicketEvent
        fields = ["id", "event_type", "actor", "actor_type", "old_value", "new_value", "note", "created_at"]


class AttachmentAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ["id", "original_filename", "size_bytes", "content_type", "created_at"]


class TicketAdminListSerializer(serializers.ModelSerializer):
    client_email = serializers.EmailField(source="client.email", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "reference",
            "subject",
            "status",
            "priority",
            "client_email",
            "reporter_name",
            "created_at",
            "updated_at",
        ]


class TicketAdminDetailSerializer(serializers.ModelSerializer):
    client_email = serializers.EmailField(source="client.email", read_only=True)
    responses = ResponseAdminSerializer(many=True, read_only=True)
    events = EventAdminSerializer(many=True, read_only=True)
    attachments = AttachmentAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "reference",
            "subject",
            "description",
            "reporter_name",
            "client_email",
            "status",
            "priority",
            "created_at",
            "updated_at",
            "resolved_at",
            "responses",
            "events",
            "attachments",
        ]


class TicketUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Status.choices, required=False)
    priority = serializers.ChoiceField(choices=Priority.choices, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one of status or priority must be provided.")
        return attrs


class ResponseCreateSerializer(serializers.Serializer):
    message = serializers.CharField()
    is_internal = serializers.BooleanField(default=False)


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
