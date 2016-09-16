from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import AtmoGoogleProvider

urlpatterns = default_urlpatterns(AtmoGoogleProvider)
