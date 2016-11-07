from allauth.account.utils import default_user_display


def email_user_display(user):
    """Return the user email address or interpolate the user instance"""
    email = getattr(user, 'email', None)
    if email is None:
        # inline import to prevent circular import via settings init
        return default_user_display(user)
    else:
        return email.split('@')[0]
