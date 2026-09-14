from django.contrib import admin

from .models import Attachment, Client, Response, Ticket, TicketAccessToken, TicketEvent


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    search_fields = ("email",)


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 0
    fields = ("author", "message", "is_internal", "created_at")
    readonly_fields = ("created_at",)


class TicketEventInline(admin.TabularInline):
    model = TicketEvent
    extra = 0
    fields = ("event_type", "actor", "actor_type", "old_value", "new_value", "created_at")
    readonly_fields = ("created_at",)


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    fields = ("original_filename", "content_type", "size_bytes", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("reference", "subject", "status", "priority", "client", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("reference", "subject", "reporter_name", "client__email")
    readonly_fields = ("reference", "created_at", "updated_at")
    inlines = [ResponseInline, TicketEventInline, AttachmentInline]


@admin.register(TicketAccessToken)
class TicketAccessTokenAdmin(admin.ModelAdmin):
    # token_hash is intentionally excluded — it is not shown in the admin
    # UI even though it is only a hash, never the raw token.
    list_display = ("ticket", "issued_for", "created_at", "expires_at", "revoked_at", "is_valid")
    list_filter = ("issued_for",)
    readonly_fields = ("created_at",)
    exclude = ("token_hash",)

    @admin.display(boolean=True)
    def is_valid(self, obj: TicketAccessToken) -> bool:
        return obj.is_valid


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)


@admin.register(TicketEvent)
class TicketEventAdmin(admin.ModelAdmin):
    list_display = ("ticket", "event_type", "actor_type", "actor", "created_at")
    list_filter = ("event_type", "actor_type")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "original_filename", "content_type", "size_bytes", "created_at")
