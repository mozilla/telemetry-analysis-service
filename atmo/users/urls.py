# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import AtmoGoogleProvider

urlpatterns = default_urlpatterns(AtmoGoogleProvider)
