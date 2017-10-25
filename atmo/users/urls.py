# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf.urls import include, url
from django.views import generic


urlpatterns = [
    url(r'login/$', generic.TemplateView.as_view(template_name='atmo/users/login.html'),
        name='users-login'),
    url(r'', include('mozilla_django_oidc.urls')),
]
