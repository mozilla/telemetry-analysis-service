import pytest
from django.utils import timezone


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def test_user(client, django_user_model):
    test_user = django_user_model.objects.create_user(
        'testuser',
        'test@example.com',
        'testpassword',
    )
    client.force_login(test_user)
    return test_user
