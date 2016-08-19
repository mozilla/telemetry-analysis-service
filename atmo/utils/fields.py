from django import forms
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat


class PublicKeyFileField(forms.FileField):
    """
    Custom Django file field that only accepts SSH public keys.

    The cleaned data is the public key as a string.
    """
    def __init__(self, *args, **kwargs):
        super(PublicKeyFileField, self).__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        uploaded_file = super(PublicKeyFileField, self).clean(data, initial)
        if uploaded_file.size > 100000:
            raise ValidationError(
                'File size must be at most 100kB, actual size is {}'.format(
                    filesizeformat(uploaded_file.size)
                )
            )
        contents = uploaded_file.read()
        if not contents.startswith('ssh-rsa AAAAB3'):
            raise ValidationError(
                'Invalid public key (a public key should start with \'ssh-rsa AAAAB3\')'
            )
        return contents
