# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
def generate_username_from_email(email):
    """
    Use the unique part of the email as the username for mozilla.com
    and the full email address for all other users.
    """
    if '@' in email and email.endswith('@mozilla.com'):
        return email.split('@')[0]
    else:
        return email
