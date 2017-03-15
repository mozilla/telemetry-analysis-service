from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django import forms


class AtmoAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        """
        We disable the signup with regular accounts as we require Persona
        (for now)
        """
        return False


class AtmoSocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_open_for_signup(self, request, sociallogin):
        """
        Specifically enable social account login.
        """
        return True

    def validate_disconnect(self, account, accounts):
        """
        Validate whether or not the socialaccount account can be
        safely disconnected.
        """
        if len(accounts) == 1:
            raise forms.ValidationError(
                'At least one account needs to be connected'
            )
