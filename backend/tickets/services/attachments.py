import logging

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework.exceptions import ValidationError

from tickets.models import Attachment, Ticket

logger = logging.getLogger(__name__)

# SVG excluded deliberately — a scriptable XSS vector. Archives excluded too.
ALLOWED_CONTENT_TYPES = {
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "gif": {"image/gif"},
    "webp": {"image/webp"},
    "pdf": {"application/pdf"},
    "txt": {"text/plain"},
    "log": {"text/plain", "text/x-log"},
    "csv": {"text/csv", "application/vnd.ms-excel"},
}


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_files(files: list[UploadedFile]) -> None:
    max_count = settings.ATTACHMENT_MAX_COUNT
    max_bytes = settings.ATTACHMENT_MAX_BYTES

    if len(files) > max_count:
        logger.warning("Attachment upload rejected: %s files exceeds max of %s", len(files), max_count)
        raise ValidationError({"attachments": [f"A maximum of {max_count} attachments is allowed."]})

    for f in files:
        ext = _extension(f.name)
        allowed_types = ALLOWED_CONTENT_TYPES.get(ext)

        if allowed_types is None:
            logger.warning("Attachment rejected: disallowed extension %r (%s)", ext, f.name)
            raise ValidationError({"attachments": [f"'{f.name}': file type is not allowed."]})

        if f.size > max_bytes:
            logger.warning("Attachment rejected: %s bytes exceeds limit for %s", f.size, f.name)
            raise ValidationError(
                {"attachments": [f"'{f.name}' exceeds the {max_bytes // (1024 * 1024)}MB size limit."]}
            )

        if f.content_type not in allowed_types:
            logger.warning("Attachment rejected: content-type %r mismatched for %s", f.content_type, f.name)
            raise ValidationError({"attachments": [f"'{f.name}': content type does not match its extension."]})


def store_files(ticket: Ticket, files: list[UploadedFile]) -> list[Attachment]:
    """Caller must have already validated `files` via validate_files()."""
    created = []
    for f in files:
        attachment = Attachment.objects.create(
            ticket=ticket,
            file=f,
            original_filename=f.name,
            content_type=f.content_type,
            size_bytes=f.size,
        )
        created.append(attachment)
    return created
