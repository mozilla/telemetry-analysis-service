# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from allauth.socialaccount.app_settings import QUERY_EMAIL
from allauth.socialaccount.providers.google.provider import (GoogleAccount,
                                                             GoogleProvider,
                                                             Scope)


class AtmoGoogleAccount(GoogleAccount):
    def get_profile_url(self):
        """
        The profile URL field is called 'profile' for OpenIDConnect profiles,
        see https://developers.google.com/+/web/api/rest/openidconnect/getOpenIdConnect
        """
        return self.account.extra_data.get('profile')


class AtmoGoogleProvider(GoogleProvider):

    def extract_uid(self, data):
        return str(data['sub'])

    def get_default_scope(self):
        "Override the default method to prepend 'openid' and add specific order"
        scope = ['openid']
        if QUERY_EMAIL:
            scope.append(Scope.EMAIL)
        scope.append(Scope.PROFILE)
        return scope

    def get_hosted_domain(self):
        "If configured returns the Google Apps domain"
        return self.get_settings().get('HOSTED_DOMAIN', None)

    def get_auth_params(self, request, action):
        "If configured, adds the hosted domain to the auth request"
        params = super().get_auth_params(request, action)
        hosted_domain = self.get_hosted_domain()
        if hosted_domain is not None:
            params['hd'] = hosted_domain
        return params


provider_classes = [AtmoGoogleProvider]
