from django.conf import settings

from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class AtmoOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def verify_claims(self, claims):
        """
        See if the claims contain a list of user groups (in various forms)
        and then check it against a configured list of allowed groups.
        """
        # shortcut in case remote groups aren't enabled
        if not settings.REMOTE_GROUPS_ENABLED:
            return True
        remote_groups = set(
            claims.get('groups') or
            claims.get('https://sso.mozilla.com/claim/groups') or
            []
        )
        allowed_groups = settings.REMOTE_GROUPS_ALLOWED
        return bool(allowed_groups.intersection(remote_groups))
