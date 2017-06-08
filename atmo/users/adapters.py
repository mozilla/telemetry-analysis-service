# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_username
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from django import forms


class AtmoAccountAdapter(DefaultAccountAdapter):
    """A custom allauth account adapter for ATMO."""

    def is_open_for_signup(self, request):
        """
        We disable the signup with regular accounts as
        we only need Google auth, returning ``False``.
        """
        return False


class AtmoSocialAccountAdapter(DefaultSocialAccountAdapter):
    """A custom allauth social account adapter for ATMO."""

    def is_open_for_signup(self, request, sociallogin):
        """
        Specifically enable social account login by returning ``True``.
        """
        return True

    def validate_disconnect(self, account, accounts):
        """
        Raises a validation error when there is only one social account
        for each user preventing the user from disabling its only login
        since we've disabled the default account system in
        :class:`~atmo.users.adapaters.AtmoAccountAdapter`.
        """
        if len(accounts) == 1:
            raise forms.ValidationError(
                'At least one account needs to be connected'
            )

    def populate_user(self, request, sociallogin, data):
        """
        When populating a :class:`~django.contrib.auth.models.User` object
        during login, we make sure the username is the user part of the
        user's email address, e.g. ``jdoe@mozilla.com`` will mean the username
        is ``jdoe``.
        """
        user = super().populate_user(request, sociallogin, data)
        email = user_email(user)
        if email and '@' in email:
            username = email.split('@')[0]
            user_username(user, username)
        return user
