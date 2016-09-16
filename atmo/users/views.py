import redis
import requests
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import (OAuth2LoginView,
                                                          OAuth2CallbackView)
from cachecontrol import CacheControl
from cachecontrol.caches.redis_cache import RedisCache
from django.core.exceptions import PermissionDenied
from django.conf import settings

from .provider import AtmoGoogleProvider


DISCOVERY_DOCUMENT_ENDPOINT = 'https://accounts.google.com/.well-known/openid-configuration'
TOKENINFO_ENDPOINT = 'https://www.googleapis.com/oauth2/v3/tokeninfo'
CACHE_CONTROL_REDIS_DB = 1

# respects HTTP cache headers here to not fetch this every time
redis_client = redis.Redis.from_url(
    settings.REDIS_URL.geturl(),
    db=CACHE_CONTROL_REDIS_DB,
)
session = CacheControl(requests.session(), RedisCache(redis_client))


def fetch_discovery_document():
    "Fetch discovery document from Google, respect cache response headers"
    response = session.get(DISCOVERY_DOCUMENT_ENDPOINT)
    response.raise_for_status()
    return response.json()


def url_endpoint(name, default=None):
    "Fetch the discovery document for the given URL endpoint name"
    discovery_document = fetch_discovery_document()
    return discovery_document.get(name, default)


class AtmoGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    provider_id = AtmoGoogleProvider.id
    access_token_url = url_endpoint(
        'token_endpoint',
        GoogleOAuth2Adapter.access_token_url
    )
    authorize_url = url_endpoint(
        'authorization_endpoint',
        GoogleOAuth2Adapter.authorize_url
    )
    profile_url = url_endpoint(
        'userinfo_endpoint',
        GoogleOAuth2Adapter.profile_url,
    )

    def complete_login(self, request, app, token, **kwargs):
        """
        Extends the default login completion by verification of response data
        as documented on:

          https://developers.google.com/identity/protocols/OpenIDConnect

        """
        response = kwargs.get('response', None)
        if response is None:
            raise PermissionDenied('Something went wrong during the login')

        # response contains data from the access token URL request
        id_token = response.get('id_token', None)
        if id_token is None:
            raise PermissionDenied('No ID received from Google')

        # verify the ID token using Google's endpoint
        response = requests.post(TOKENINFO_ENDPOINT, data={'id_token': id_token})
        response.raise_for_status()
        id_token_data = response.json()

        # verify the received audience token with the client ID we have
        provider = self.get_provider()
        if provider.get_app(request).client_id != id_token_data.get('aud', None):
            raise PermissionDenied('Invalid client ID received')

        # if configured, check if the return hosted domain matches what we have
        hosted_domain = provider.get_hosted_domain()
        if hosted_domain and hosted_domain != id_token_data.get('hd', None):
            raise PermissionDenied('Access restricted to users of '
                                   'the domain %s' % hosted_domain)

        return super(AtmoGoogleOAuth2Adapter, self).complete_login(
            request, app, token, **kwargs
        )


oauth2_login = OAuth2LoginView.adapter_view(AtmoGoogleOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(AtmoGoogleOAuth2Adapter)
