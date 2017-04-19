# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from allauth.account.utils import default_user_display


def email_user_display(user):
    """Return the user email address or interpolate the user instance"""
    email = getattr(user, 'email', None)
    if email is None:
        # inline import to prevent circular import via settings init
        return default_user_display(user)
    else:
        return email.split('@')[0]
