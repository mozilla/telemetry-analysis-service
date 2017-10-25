def generate_username_from_email(email):
    """
    Use the unique part of the email as the username for mozilla.com
    and the full email address for all other users.
    """
    if '@' in email and email.endswith('@mozilla.com'):
        return email.split('@')[0]
    else:
        return email
