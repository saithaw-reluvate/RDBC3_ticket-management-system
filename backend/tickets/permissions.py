from rest_framework.permissions import BasePermission


class IsStaffUser(BasePermission):
    """Admin plane: session auth + is_staff. Never sequential-ID trust."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
