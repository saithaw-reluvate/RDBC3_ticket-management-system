import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from tickets.models import Attachment

pytestmark = pytest.mark.django_db


def _upload(name="report.pdf", content=b"%PDF-1.4 fake content"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def test_attachment_created_with_randomized_path(ticket):
    attachment = Attachment.objects.create(
        ticket=ticket,
        file=_upload(),
        original_filename="report.pdf",
        content_type="application/pdf",
        size_bytes=22,
    )
    assert attachment.pk is not None
    assert attachment.file.name != "report.pdf"
    assert "report.pdf" in attachment.file.name
    attachment.file.delete(save=False)


def test_size_bytes_must_be_positive(ticket):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Attachment.objects.create(
                ticket=ticket,
                file=_upload(),
                original_filename="empty.txt",
                content_type="text/plain",
                size_bytes=0,
            )


def test_multiple_attachments_per_ticket(ticket):
    a1 = Attachment.objects.create(
        ticket=ticket,
        file=_upload("a.txt", b"a"),
        original_filename="a.txt",
        content_type="text/plain",
        size_bytes=1,
    )
    a2 = Attachment.objects.create(
        ticket=ticket,
        file=_upload("b.txt", b"bb"),
        original_filename="b.txt",
        content_type="text/plain",
        size_bytes=2,
    )
    assert ticket.attachments.count() == 2
    a1.file.delete(save=False)
    a2.file.delete(save=False)
