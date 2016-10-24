from urlparse import urlparse
import pytest
from django.contrib.sites.models import Site


@pytest.mark.django_db
def test_initial_site(settings):
    "Test if the site migration uses the env var SITE_URL"
    domain = urlparse(settings.SITE_URL)
    assert Site.objects.get_current().domain, domain.netloc
