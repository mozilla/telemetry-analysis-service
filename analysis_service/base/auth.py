from django_browserid.auth import BrowserIDBackend


class AllowMozillaEmailsBackend(BrowserIDBackend):
    def is_valid_email(self, email):
        return email.endswith("@mozilla.com")
