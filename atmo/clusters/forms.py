from django import forms

from . import models
from ..utils.fields import PublicKeyFileField


class NewClusterForm(forms.ModelForm):
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
    size = forms.IntegerField(
        required=True,
        min_value=1, max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'min': '1', 'max': '20',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Number of workers to use in the cluster '
                            '(1 is recommended for testing or development).',
        })
    )
    public_key = PublicKeyFileField(
        required=True,
        widget=forms.FileInput(attrs={'required': 'required'})
    )

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(NewClusterForm, self).__init__(*args, **kwargs)

    def save(self):
        # create the model without committing, since we haven't
        # set the required created_by field yet
        new_cluster = super(NewClusterForm, self).save(commit=False)

        # set the field to the user that created the cluster
        new_cluster.created_by = self.created_by

        # actually start the real cluster, and return the model object
        new_cluster.save()

    class Meta:
        model = models.Cluster
        fields = ['identifier', 'size', 'public_key', 'emr_release']


class EditClusterForm(forms.ModelForm):
    cluster = forms.ModelChoiceField(
        queryset=models.Cluster.objects.all(),
        required=True,
        widget=forms.HiddenInput(attrs={
            # fields with the `selected-cluster` class get their value automatically
            # set to the cluster ID of the selected cluster
            'class': 'selected-cluster',
        })
    )

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

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(EditClusterForm, self).__init__(*args, **kwargs)

    def save(self):
        cleaned_data = super(EditClusterForm, self).clean()
        cluster = cleaned_data["cluster"]
        if self.created_by != cluster.created_by:  # only allow editing clusters that one created
            raise ValueError("Disallowed attempt to edit another user's cluster")
        cluster.identifier = cleaned_data["identifier"]
        cluster.update_identifier()
        cluster.save()

    class Meta:
        model = models.Cluster
        fields = ['identifier']


class DeleteClusterForm(forms.ModelForm):
    cluster = forms.ModelChoiceField(
        queryset=models.Cluster.objects.all(),
        required=True,
        widget=forms.HiddenInput(attrs={
            # fields with the `selected-cluster` class get their value automatically
            # set to the cluster ID of the selected cluster
            'class': 'selected-cluster',
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(DeleteClusterForm, self).__init__(*args, **kwargs)

    def save(self):
        cleaned_data = super(DeleteClusterForm, self).clean()
        cluster = cleaned_data["cluster"]
        if self.created_by != cluster.created_by:  # only allow deleting clusters that one created
            raise ValueError("Disallowed attempt to delete another user's cluster")
        cluster.deactivate()

    class Meta:
        model = models.Cluster
        fields = []
