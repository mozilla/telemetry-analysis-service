# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms

from . import models
from ..forms import CreatedByFormMixin, PublicKeyFileField


class NewClusterForm(CreatedByFormMixin, forms.ModelForm):

    identifier = forms.RegexField(
        label="Cluster identifier",
        required=True,
        regex="^[\w-]{1,100}$",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        }),
        help_text='A brief description of the cluster\'s purpose, '
                  'visible in the AWS management console.',
    )
    size = forms.IntegerField(
        label="Cluster size",
        required=True,
        min_value=1, max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'min': '1',
            'max': '20',
        }),
        help_text='Number of workers to use in the cluster '
                  '(1 is recommended for testing or development).'
    )
    public_key = PublicKeyFileField(
        label="Public SSH key",
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'required': 'required'}),
        help_text="""\
Upload your SSH <strong>public key</strong>, not private key!
This will generally be found in places like <code>~/.ssh/id_rsa.pub</code>.
"""
    )
    emr_release = forms.ChoiceField(
        choices=models.Cluster.EMR_RELEASES_CHOICES,
        widget=forms.Select(
            attrs={'class': 'form-control', 'required': 'required'}
        ),
        label='EMR release version',
        initial=models.Cluster.EMR_RELEASES_CHOICES_DEFAULT,
    )

    def save(self, commit=False):
        # create the model without committing, since we haven't
        # set the required created_by field yet
        cluster = super(NewClusterForm, self).save(commit=commit)

        # set the field to the user that created the cluster
        cluster.created_by = self.created_by

        # actually start the real cluster, and return the model object
        cluster.save()
        return cluster

    class Meta:
        model = models.Cluster
        fields = ['identifier', 'size', 'public_key', 'emr_release']


class EditClusterForm(CreatedByFormMixin, forms.ModelForm):
    identifier = forms.RegexField(
        required=True,
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': r'[\w-]+',
        }),
        help_text='A brief description of the cluster\'s purpose, '
                  'visible in the AWS management console.',
    )

    def save(self, commit=True):
        cluster = super(EditClusterForm, self).save(commit=False)
        cluster.update_identifier()
        if commit:
            cluster.save()
            self.save_m2m()
        return cluster

    class Meta:
        model = models.Cluster
        fields = ['identifier']


class TerminateClusterForm(CreatedByFormMixin, forms.ModelForm):
    confirmation = forms.RegexField(
        required=True,
        label='Confirm termination with cluster identifier',
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        }),
    )

    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation')
        if confirmation != self.instance.identifier:
            raise forms.ValidationError(
                "Entered cluster identifier doesn't match"
            )
        return confirmation

    class Meta:
        model = models.Cluster
        fields = []
