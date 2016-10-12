from django import forms

from . import models
from ..utils.fields import PublicKeyFileField


class ClusterFormMixin(object):

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(ClusterFormMixin, self).__init__(*args, **kwargs)

    def clean(self):
        """
        only allow deleting clusters that one created
        """
        super(ClusterFormMixin, self).clean()
        if self.instance.id and self.created_by != self.instance.created_by:
            raise forms.ValidationError(
                "Access denied to a cluster of another user"
            )


class NewClusterForm(ClusterFormMixin, forms.ModelForm):

    identifier = forms.RegexField(
        label="Cluster identifier",
        required=True,
        regex="^[\w-]{1,100}$",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'pattern': r'[\w-]+',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'A brief description of the cluster\'s purpose, '
                            'visible in the AWS management console.',
            'data-validation-pattern-message': 'Valid cluster names are strings of alphanumeric '
                                               'characters, \'_\', and \'-\'.',
        })
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
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Number of workers to use in the cluster '
                            '(1 is recommended for testing or development).',
        })
    )
    public_key = PublicKeyFileField(
        label="Public SSH key",
        required=True,
        widget=forms.FileInput(attrs={'required': 'required'}),
        help_text="""\
Upload your SSH <strong>public key</strong>, not private key!
This will generally be found in places like <code>~/.ssh/id_rsa.pub</code>.
"""
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


class EditClusterForm(ClusterFormMixin, forms.ModelForm):
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
            'data-content': 'A brief description of the cluster\'s purpose, '
                            'visible in the AWS management console.',
            'data-validation-pattern-message': 'Valid cluster names are strings of alphanumeric '
                                               'characters, \'_\', and \'-\'.',
        })
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


class TerminateClusterForm(ClusterFormMixin, forms.ModelForm):
    confirmation = forms.RegexField(
        required=True,
        label='Confirm termination with cluster identifier',
        regex="^[\w-]{1,100}$",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        }),
    )

    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation', None)
        if confirmation != self.instance.identifier:
            raise forms.ValidationError(
                "Entered cluster identifier doesn't match"
            )
        return confirmation

    class Meta:
        model = models.Cluster
        fields = []
