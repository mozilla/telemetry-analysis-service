# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.utils import dateformat, timezone
from django.utils.safestring import mark_safe

from . import models
from .. import scheduling
from ..forms.fields import CachedFileField
from ..forms.mixins import (
    CachedFileModelFormMixin, CreatedByModelFormMixin, FormControlFormMixin
)


class BaseSparkJobForm(FormControlFormMixin, CachedFileModelFormMixin,
                       CreatedByModelFormMixin, forms.ModelForm):
    identifier = forms.RegexField(
        required=True,
        label='Job identifier',
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'required': 'required',
            'class': 'identifier-taken-check',
            'data-identifier-taken-check-url': reverse_lazy('jobs-identifier-taken'),
        }),
        help_text='A unique identifier to identify your Spark job, visible in '
                  'the AWS management console. (Lowercase, use hyphens instead of spaces.)'
    )
    description = forms.CharField(
        required=True,
        label='Job description',
        strip=True,
        widget=forms.Textarea(attrs={
            'required': 'required',
            'rows': 2,
        }),
        help_text='A brief description of your Spark job\'s purpose. This is '
                  'intended to provide extra context for the data engineering team.'
    )
    result_visibility = forms.ChoiceField(
        choices=models.SparkJob.RESULT_VISIBILITY_CHOICES,
        widget=forms.Select(attrs={
            'required': 'required',
        }),
        label='Job result visibility',
        help_text='Whether notebook results are uploaded to a public '
                  'or private bucket',
    )
    size = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=settings.AWS_CONFIG['MAX_CLUSTER_SIZE'],
        label='Job cluster size',
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
        widget=forms.Select(attrs={
            'required': 'required',
        }),
        label='Job interval',
        help_text='Interval at which the Spark job should be run',
    )
    job_timeout = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=24,
        label='Job timeout',
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
            'class': 'datetimepicker',
        }),
        label='Job start date (UTC)',
        help_text='Date and time of when the scheduled Spark job should '
                  'start running.',
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'datetimepicker',
        }),
        label='Job end date (UTC)',
        help_text='Optional date and time of when the scheduled Spark job '
                  'should stop running - leave this blank if the job should '
                  'not be disabled.',
    )
    notebook = CachedFileField(
        required=True,
        widget=forms.FileInput(),  # no need to specific required attr here
        label='Analysis Jupyter Notebook',
        help_text='A Jupyter/IPython Notebook with a file ipynb '
                  'extension.'
    )

    def __init__(self, *args, **kwargs):
        super(BaseSparkJobForm, self).__init__(*args, **kwargs)
        now = dateformat.format(timezone.now(), settings.DATETIME_FORMAT)
        self.fields['start_date'].label = mark_safe(
            '%s <small>Currently: %s</small>' %
            (self.fields['start_date'].label, now)
        )
        self.fields['end_date'].label = mark_safe(
            '%s <small>Currently: %s</small>' %
            (self.fields['end_date'].label, now)
        )

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
        spark_job = super(BaseSparkJobForm, self).save(commit=False)
        # if notebook was specified, replace the current notebook
        if 'notebook' in self.changed_data:
            spark_job.notebook_s3_key = scheduling.spark_job_add(
                self.cleaned_data['identifier'],
                self.cleaned_data['notebook']
            )

        if commit:
            # actually save the scheduled Spark job, and return the model object
            spark_job.save()
        return spark_job


class NewSparkJobForm(BaseSparkJobForm):
    prefix = 'new'

    class Meta(BaseSparkJobForm.Meta):
        fields = BaseSparkJobForm.Meta.fields + ['emr_release']


class EditSparkJobForm(BaseSparkJobForm):
    prefix = 'edit'
    identifier = forms.CharField(
        disabled=True,
        label='Job identifier',
        widget=forms.TextInput(attrs={'required': 'required'}),
        help_text='A brief description of the scheduled Spark job\'s purpose, '
                  'visible in the AWS management console.'
    )

    notebook = CachedFileField(
        required=False,
        widget=forms.FileInput(),
        label='Analysis Jupyter Notebook',
        help_text='Optional Jupyter/IPython Notebook with a file ipynb '
                  'extension.'
    )

    start_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={
            'class': 'datetimepicker',
        }),
        label='Job start date (UTC)',
        help_text='Date and time of when the scheduled Spark job should '
                  'start running. Changing this field will reset the job '
                  'schedule. Only future dates are allowed.',
    )

    def __init__(self, *args, **kwargs):
        super(EditSparkJobForm, self).__init__(*args, **kwargs)
        self.fields['notebook'].help_text += (
            '<br />Current notebook: <strong>%s</strong>' % self.instance.notebook_name
        )

    def clean_start_date(self):
        if ('start_date' in self.changed_data and
                self.cleaned_data['start_date'] < timezone.now()):
            raise forms.ValidationError('You can only move start_date to a future date')
        return self.cleaned_data['start_date']

    def save(self, commit=True):
        obj = super(EditSparkJobForm, self).save(commit=False)
        if 'start_date' in self.changed_data:
            # If the start_date changed it must be set in the future
            # per the validation rule above.
            # Reset the last_run_date so that it runs at start_date.
            obj.last_run_date = None
        if commit:
            obj.save()
        return obj


class TakenSparkJobForm(forms.Form):
    id = forms.IntegerField(required=False)
    identifier = forms.CharField(required=True)
