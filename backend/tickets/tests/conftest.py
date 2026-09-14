import django.template.base as _template_base
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from tickets.constants import Category, IssuedFor, Priority, Status
from tickets.models import Client, Ticket

# Captured at import time, before pytest-django's setup_test_environment()
# monkeypatches Template._render for assertTemplateUsed-style assertions
# (which this project never uses).
_original_template_render = _template_base.Template._render


@pytest.fixture(autouse=True)
def _fix_py314_template_render_copy_bug():
    # Under Python 3.14, Django's test-only render instrumentation breaks:
    # its `copy.copy(super())` trick to snapshot the Context raises
    # AttributeError. That instrumentation is unused here, so restore the
    # real Template._render before every test — needed because render_to_string()
    # is used for outbound email bodies.
    _template_base.Template._render = _original_template_render


@pytest.fixture(autouse=True)
def _use_locmem_email_backend(settings):
    # Real SMTP (Mailpit) is used for manual/Postman verification; automated
    # tests never need a live server for this.
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    # DRF throttles are cache-backed; without this, throttle state leaks
    # between tests that hit the same view.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def admin_api_client(api_client, staff_user) -> APIClient:
    api_client.force_login(staff_user)
    return api_client


@pytest.fixture
def ticket_client(db) -> Client:
    return Client.objects.create(email="Customer@Example.com")


@pytest.fixture
def ticket(db, ticket_client) -> Ticket:
    return Ticket.objects.create(
        client=ticket_client,
        reporter_name="Jane Customer",
        subject="Cannot access account",
        description="Login fails with a 500 error.",
        category=Category.ACCOUNT_ACCESS,
        status=Status.OPEN,
        priority=Priority.MEDIUM,
    )


@pytest.fixture
def staff_user(db):
    User = get_user_model()
    return User.objects.create_user(username="admin1", password="not-a-real-password", is_staff=True)


@pytest.fixture
def issued_for():
    return IssuedFor.INITIAL
