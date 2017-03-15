from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            dest='client_id',
            required=True,
            help='The Google client ID',
        )
        parser.add_argument(
            '--client-secret',
            dest='client_secret',
            required=True,
            help='The Google client secret',
        )

    def handle(self, *args, **options):
        SocialApp.objects.all().delete()
        self.stdout.write('Removed all other credentials.')
        social_app = SocialApp.objects.create(
            provider='google',
            name='Googe',
            client_id=options['client_id'],
            secret=options['client_secret'],
        )
        social_app.sites.add(Site.objects.get_current())
        self.stdout.write('Added Google credentials for client ID "%s".' %
                          options['client_id'])
