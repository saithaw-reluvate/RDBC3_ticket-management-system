import logging

from django.contrib.auth import authenticate, login, logout
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as DRFResponse
from rest_framework.views import APIView

from tickets.constants import ActorType, EventType, IssuedFor
from tickets.models import Attachment, Ticket
from tickets.permissions import IsStaffUser
from tickets.serializers import (
    AdminLoginSerializer,
    ResponseAdminSerializer,
    ResponseCreateSerializer,
    TicketAdminDetailSerializer,
    TicketAdminListSerializer,
    TicketUpdateSerializer,
)
from tickets.services import events as events_service
from tickets.services import emails as emails_service
from tickets.services import tickets as tickets_service
from tickets.services import tokens as tokens_service

logger = logging.getLogger(__name__)


class AdminLoginView(APIView):
    """POST /api/admin/auth/login/ — session login. Requires a CSRF cookie
    already set (GET /api/admin/auth/me/ primes it)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_staff:
            logger.warning("Admin login failed: username=%s", serializer.validated_data["username"])
            raise AuthenticationFailed("Invalid credentials.")

        login(request, user)
        logger.info("Admin login succeeded: user_id=%s", user.id)
        return DRFResponse({"username": user.username, "is_staff": user.is_staff})


class AdminLogoutView(APIView):
    """POST /api/admin/auth/logout/ — end session."""

    permission_classes = [IsStaffUser]

    def post(self, request):
        logger.info("Admin logout: user_id=%s", request.user.id)
        logout(request)
        return DRFResponse(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AdminMeView(APIView):
    """GET /api/admin/auth/me/ — current user; always sets the csrftoken
    cookie (via ensure_csrf_cookie) so a caller can log in next."""

    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated or not request.user.is_staff:
            raise AuthenticationFailed("Not authenticated.")
        return DRFResponse({"username": request.user.username, "is_staff": request.user.is_staff})


class AdminTicketListView(generics.ListAPIView):
    """GET /api/admin/tickets/ — filter by status/priority, search, order,
    paginated."""

    permission_classes = [IsStaffUser]
    serializer_class = TicketAdminListSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["reference", "subject", "reporter_name", "client__email"]
    ordering_fields = ["created_at", "priority", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Ticket.objects.select_related("client")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        priority_param = self.request.query_params.get("priority")
        if priority_param:
            qs = qs.filter(priority=priority_param)
        return qs


class AdminTicketDetailView(APIView):
    """GET/PATCH /api/admin/tickets/<reference>/ — keyed on reference, never
    the primary key. GET returns all responses (including internal) and all
    events. PATCH updates status and/or priority."""

    permission_classes = [IsStaffUser]

    def get_object(self, reference: str) -> Ticket:
        return get_object_or_404(
            Ticket.objects.select_related("client").prefetch_related("responses", "events", "attachments"),
            reference=reference,
        )

    def get(self, request, reference):
        ticket = self.get_object(reference)
        return DRFResponse(TicketAdminDetailSerializer(ticket).data)

    def patch(self, request, reference):
        ticket = self.get_object(reference)
        serializer = TicketUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "status" in data:
            ticket = tickets_service.update_status(ticket, data["status"], actor=request.user)
        if "priority" in data:
            ticket = tickets_service.update_priority(ticket, data["priority"], actor=request.user)

        return DRFResponse(TicketAdminDetailSerializer(ticket).data)


class AdminResponseCreateView(APIView):
    """POST /api/admin/tickets/<reference>/responses/ — add a response."""

    permission_classes = [IsStaffUser]

    def post(self, request, reference):
        ticket = get_object_or_404(Ticket, reference=reference)
        serializer = ResponseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_obj = tickets_service.add_response(ticket, author=request.user, **serializer.validated_data)

        return DRFResponse(ResponseAdminSerializer(response_obj).data, status=status.HTTP_201_CREATED)


class AdminResendLinkView(APIView):
    """POST /api/admin/tickets/<reference>/resend-link/ — mint a new token
    and email it."""

    permission_classes = [IsStaffUser]

    def post(self, request, reference):
        ticket = get_object_or_404(Ticket, reference=reference)
        _, raw_token = tokens_service.issue_token(ticket, issued_for=IssuedFor.RESEND)
        events_service.record(ticket, EventType.TOKEN_ISSUED, actor=request.user, actor_type=ActorType.ADMIN)
        emails_service.send_link_resend(ticket, raw_token)
        return DRFResponse({"message": "Tracking link resent."})


class AdminRevokeLinksView(APIView):
    """POST /api/admin/tickets/<reference>/revoke-links/ — revoke all active
    tokens for the ticket."""

    permission_classes = [IsStaffUser]

    def post(self, request, reference):
        ticket = get_object_or_404(Ticket, reference=reference)
        count = tokens_service.revoke_active_tokens(ticket)
        events_service.record(
            ticket,
            EventType.TOKEN_REVOKED,
            actor=request.user,
            actor_type=ActorType.ADMIN,
            note=f"{count} token(s) revoked",
        )
        return DRFResponse({"revoked": count})


class AdminAttachmentDownloadView(APIView):
    """GET /api/admin/tickets/<reference>/attachments/<id>/ — download."""

    permission_classes = [IsStaffUser]

    def get(self, request, reference, attachment_id):
        ticket = get_object_or_404(Ticket, reference=reference)
        try:
            attachment = ticket.attachments.get(id=attachment_id)
        except Attachment.DoesNotExist:
            raise NotFound("Attachment not found.")

        response = FileResponse(
            attachment.file.open("rb"), as_attachment=True, filename=attachment.original_filename
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
