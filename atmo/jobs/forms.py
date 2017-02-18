# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import dateformat, timezone
from django.utils.safestring import mark_safe

from . import models
from ..forms.fields import CachedFileField
from ..forms.mixins import (
    CachedFileModelFormMixin, CreatedByModelFormMixin, AutoClassFormMixin
)


class BaseSparkJobForm(AutoClassFormMixin, CachedFileModelFormMixin,
                       CreatedByModelFormMixin, forms.ModelForm):
    identifier = forms.RegexField(
        required=True,
        label='Identifier',
        regex=r'^[a-z0-9-]{1,100}$',
        widget=forms.TextInput(attrs={
            'required': 'required',
            'pattern': r'[a-z0-9-]{1,100}',
            'data-parsley-pattern-message': 'Identifier contains invalid characters.',
        }),
        help_text='A unique identifier to identify your Spark job, visible in '
                  'the AWS management console. (Lowercase, use hyphens '
                  'instead of spaces.)'
    )
    description = forms.CharField(
        required=True,
        label='Description',
        strip=True,
        widget=forms.Textarea(attrs={
            'required': 'required',
            'rows': 2,
        }),
        help_text="A brief description of your Spark job's purpose. "
                  "This is intended to provide extra context for the "
                  "data engineering team."
    )
    result_visibility = forms.ChoiceField(
        choices=models.SparkJob.RESULT_VISIBILITY_CHOICES,
        widget=forms.RadioSelect(attrs={
            'required': 'required',
            'class': 'radioset',
        }),
        label='Result visibility',
        help_text='Whether notebook results are uploaded to a public '
                  'or private S3 bucket.',
    )
    size = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=settings.AWS_CONFIG['MAX_CLUSTER_SIZE'],
        label='Cluster size',
        widget=forms.NumberInput(attrs={
            'required': 'required',
            'min': '1',
            'max': str(settings.AWS_CONFIG['MAX_CLUSTER_SIZE']),
        }),
        help_text='Number of workers to use when running the Spark job '
                  '(1 is recommended for testing or development).'
    )
    interval_in_hours = forms.ChoiceField(
        choices=models.SparkJob.INTERVAL_CHOICES,
        widget=forms.RadioSelect(attrs={
            'required': 'required',
            'class': 'radioset',
        }),
        label='Run interval',
        help_text='Interval at which the Spark job should be run.',
    )
    job_timeout = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=24,
        label='Timeout',
        widget=forms.NumberInput(attrs={
            'required': 'required',
            'min': '1',
            'max': '24',
        }),
        help_text='Number of hours that a single run of the job can run '
                  'for before timing out and being terminated.'
    )
    start_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={
            'required': 'required',
            'class': 'datetimepicker',
        }),
        label='Start date',
        help_text='Date and time of when the scheduled Spark job should '
                  'start running.',
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'datetimepicker',
        }),
        label='End date',
        help_text='Date and time of when the scheduled Spark job should '
                  'stop running - leave this blank if the job should '
                  'not be disabled.',
    )
    notebook = CachedFileField(
        required=True,
        widget=forms.FileInput(attrs={
            'accept': '.ipynb',
            'required': 'required',
        }),
        label='Analysis Jupyter Notebook',
        help_text='A Jupyter/IPython Notebook with a .ipynb file extension.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now = dateformat.format(timezone.now(), settings.DATETIME_FORMAT)
        self.fields['start_date'].label = mark_safe(
            '%s <span class="optional-label">(UTC) Currently: %s</span>' %
            (self.fields['start_date'].label, now)
        )
        self.fields['end_date'].label = mark_safe(
            '%s <span class="optional-label">(UTC) Currently: %s</span>' %
            (self.fields['end_date'].label, now)
        )
        self.fields['identifier'].widget.attrs.update({
            'data-parsley-remote': (
                reverse('jobs-identifier-available') + '?identifier={value}'
            ),
            'data-parsley-remote-reverse': 'true',
            'data-parsley-remote-message': 'Identifier unavailable',
            'data-parsley-debounce': '500',
        })

    class Meta:
        model = models.SparkJob
        fields = [
            'identifier', 'description', 'result_visibility', 'size',
            'interval_in_hours', 'job_timeout', 'start_date', 'end_date'
        ]

    @property
    def field_order(self):
        """
        Copy the defined model form fields and insert the
        notebook field at the second spot
        """
        fields = self._meta.fields[:]
        fields.insert(2, 'notebook')
        return fields

    def clean_notebook(self):
        notebook_file = self.cleaned_data['notebook']
        if notebook_file and not notebook_file.name.endswith(('.ipynb',)):
            raise forms.ValidationError('Only Jupyter/IPython Notebooks are '
                                        'allowed to be uploaded')
        return notebook_file

    def save(self, commit=True):
        # create the model without committing, since we haven't
        # set the required created_by field yet
        spark_job = super().save(commit=False)
        # if notebook was specified, replace the current notebook
        if 'notebook' in self.changed_data:
            spark_job.notebook_s3_key = self.instance.provisioner.add(
                identifier=self.cleaned_data['identifier'],
                notebook_file=self.cleaned_data['notebook']
            )

        if commit:
            # actually save the scheduled Spark job, and return the model object
            spark_job.save()
        return spark_job


class NewSparkJobForm(BaseSparkJobForm):
    prefix = 'new'

    class Meta(BaseSparkJobForm.Meta):
        fields = BaseSparkJobForm.Meta.fields + ['emr_release']
        widgets = {
            'emr_release': forms.RadioSelect(attrs={
                'required': 'required',
                'class': 'radioset',
            }),
        }


class EditSparkJobForm(BaseSparkJobForm):
    prefix = 'edit'
    notebook = CachedFileField(
        required=False,
        widget=forms.FileInput(attrs={'accept': '.ipynb'}),
        label='Analysis Jupyter Notebook',
        help_text='A Jupyter/IPython Notebook with a .ipynb file extension.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identifier'].disabled = True
        self.fields['notebook'].help_text += (
            '<br />Current notebook: <strong>%s</strong>' % self.instance.notebook_name
        )
        self.fields['start_date'].help_text += (
            'Changing this field will reset the job schedule. '
            'Only future dates are allowed.'
        )

    def clean_start_date(self):
        if ('start_date' in self.changed_data and
                self.cleaned_data['start_date'] < timezone.now()):
            raise forms.ValidationError('You can only move start_date to a future date')
        return self.cleaned_data['start_date']


class SparkJobAvailableForm(forms.Form):
    identifier = forms.CharField(required=True)
