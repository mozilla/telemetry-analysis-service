from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase

from urlparse import urlparse


class TestSite(TestCase):

    def test_initial_site(self):
        domain = urlparse(settings.SITE_URL)
        self.assertEqual(Site.objects.get_current().domain, domain.netloc)
