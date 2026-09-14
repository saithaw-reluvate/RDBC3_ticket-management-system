from django.urls import path

from tickets.views import admin as admin_views
from tickets.views import customer, public

urlpatterns = [
    # Public plane
    path("tickets/", public.TicketCreateView.as_view(), name="ticket-create"),
    path("tickets/resend-link/", public.ResendLinkView.as_view(), name="ticket-resend-link"),
    # Customer plane
    path("track/<str:token>/", customer.TicketTrackView.as_view(), name="ticket-track"),
    path(
        "track/<str:token>/attachments/<int:attachment_id>/",
        customer.AttachmentDownloadView.as_view(),
        name="ticket-track-attachment",
    ),
    # Admin plane
    path("admin/auth/login/", admin_views.AdminLoginView.as_view(), name="admin-login"),
    path("admin/auth/logout/", admin_views.AdminLogoutView.as_view(), name="admin-logout"),
    path("admin/auth/me/", admin_views.AdminMeView.as_view(), name="admin-me"),
    path("admin/tickets/", admin_views.AdminTicketListView.as_view(), name="admin-ticket-list"),
    path(
        "admin/tickets/<str:reference>/",
        admin_views.AdminTicketDetailView.as_view(),
        name="admin-ticket-detail",
    ),
    path(
        "admin/tickets/<str:reference>/responses/",
        admin_views.AdminResponseCreateView.as_view(),
        name="admin-ticket-responses",
    ),
    path(
        "admin/tickets/<str:reference>/resend-link/",
        admin_views.AdminResendLinkView.as_view(),
        name="admin-ticket-resend-link",
    ),
    path(
        "admin/tickets/<str:reference>/revoke-links/",
        admin_views.AdminRevokeLinksView.as_view(),
        name="admin-ticket-revoke-links",
    ),
    path(
        "admin/tickets/<str:reference>/attachments/<int:attachment_id>/",
        admin_views.AdminAttachmentDownloadView.as_view(),
        name="admin-ticket-attachment",
    ),
]
