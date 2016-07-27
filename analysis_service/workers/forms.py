from django import forms

from . import models
from ..utils.fields import PublicKeyFileField


class NewWorkerForm(forms.ModelForm):
    identifier = forms.RegexField(
        required=True,
        regex="^[\w-]{1,100}$",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': r'[\w-]+',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'A brief description of the worker\'s purpose, '
                            'visible in the AWS management console.',
            'data-validation-pattern-message': 'Valid worker names are strings of alphanumeric '
                                               'characters, \'_\', and \'-\'.',
        })
    )
    public_key = PublicKeyFileField(
        required=True,
        widget=forms.FileInput(attrs={'required': 'required'})
    )

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(NewWorkerForm, self).__init__(*args, **kwargs)

    def save(self):
        # create the model without committing, since we haven't
        # set the required created_by field yet
        new_worker = super(NewWorkerForm, self).save(commit=False)

        # set the field to the user that created the worker
        new_worker.created_by = self.created_by

        # actually start the real worker, and return the model object
        new_worker.save()

    class Meta:
        model = models.Worker
        fields = ['identifier', 'public_key']
