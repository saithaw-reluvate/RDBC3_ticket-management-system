from django.http import FileResponse
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as DRFResponse
from rest_framework.views import APIView

from tickets.models import Attachment
from tickets.serializers import TicketCustomerDetailSerializer
from tickets.services import tokens as tokens_service
from tickets.throttles import TokenLookupThrottle


class TicketTrackView(APIView):
    """GET /api/track/<token>/ — one composite response: status, history,
    responses, attachments. Read-only, scoped to the token's own ticket."""

    permission_classes = [AllowAny]
    throttle_classes = [TokenLookupThrottle]

    def get(self, request, token):
        ticket = tokens_service.resolve_token(token)
        return DRFResponse(TicketCustomerDetailSerializer(ticket).data)


class AttachmentDownloadView(APIView):
    """GET /api/track/<token>/attachments/<id>/ — 404 if the attachment does
    not belong to the token's own ticket."""

    permission_classes = [AllowAny]
    throttle_classes = [TokenLookupThrottle]

    def get(self, request, token, attachment_id):
        ticket = tokens_service.resolve_token(token)
        try:
            attachment = ticket.attachments.get(id=attachment_id)
        except Attachment.DoesNotExist:
            raise NotFound("Attachment not found.")

        response = FileResponse(
            attachment.file.open("rb"), as_attachment=True, filename=attachment.original_filename
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
