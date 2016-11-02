import io
import pytest
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile


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


@pytest.fixture
def notebook_maker():
    def maker(extension='ipynb'):
        return InMemoryUploadedFile(
            file=io.BytesIO('{}'),
            field_name='notebook',
            name='test-notebook.%s' % extension,
            content_type='text/plain',
            size=2,
            charset='utf8',
        )
    return maker
