def generate_username_from_email(email):
    """
    Use the unique part of the email as the username. There is a risk
    that there may be overlap between mozilla.org and mozillafoundation.org
    email addresses, but I don't think it'll be a real world issue.
    """
    if '@' in email:
        return email.split('@')[0]
    else:
        return email
