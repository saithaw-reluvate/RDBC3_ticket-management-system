from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as DRFResponse
from rest_framework.views import APIView

from tickets.serializers import ResendLinkSerializer, TicketCreateResponseSerializer, TicketCreateSerializer
from tickets.services import tickets as tickets_service
from tickets.throttles import ResendLinkThrottle, TicketCreateThrottle


class TicketCreateView(APIView):
    """POST /api/tickets/ — public, anonymous, throttled. Returns `reference`
    only; the tracking link is delivered by email (Decision 1)."""

    # No SessionAuthentication: DRF's SessionAuthentication enforces CSRF
    # for ANY request that resolves to an active session user, regardless of
    # permission_classes — so with the global default authentication classes,
    # a browser holding an unrelated admin session cookie would get a CSRF
    # 403 on this public, anonymous endpoint. This view never uses request.user
    # for anything, so it must not run session-based authentication at all.
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [TicketCreateThrottle]

    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        files = request.FILES.getlist("attachments") or request.FILES.getlist("attachments[]")

        ticket = tickets_service.create_ticket(files=files, **serializer.validated_data)

        return DRFResponse(TicketCreateResponseSerializer(ticket).data, status=status.HTTP_201_CREATED)


class ResendLinkView(APIView):
    """POST /api/tickets/resend-link/ — constant response regardless of
    whether the address is known (Decision 2), throttled against enumeration."""

    # See TicketCreateView above: must stay usable regardless of any
    # existing admin session, so no SessionAuthentication/CSRF here.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ResendLinkThrottle]

    def post(self, request):
        serializer = ResendLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tickets_service.resend_links_for_email(serializer.validated_data["email"])

        return DRFResponse(
            {"message": "If that address has tickets, a tracking link has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )
