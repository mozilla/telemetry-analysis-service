# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms

from . import models
from ..forms import CreatedByFormMixin


class BaseSparkJobForm(CreatedByFormMixin, forms.ModelForm):
    identifier = forms.RegexField(
        required=True,
        label='Job identifier',
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        }),
        help_text='A brief description of the scheduled Spark job\'s purpose, '
                  'visible in the AWS management console.'
    )
    result_visibility = forms.ChoiceField(
        choices=models.SparkJob.RESULT_VISIBILITY_CHOICES,
        widget=forms.Select(
            attrs={'class': 'form-control', 'required': 'required'}
        ),
        label='Job result visibility'
    )
    size = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=20,
        label='Job cluster size',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'min': '1',
            'max': '20',
        }),
        help_text='Number of workers to use when running the Spark job '
                  '(1 is recommended for testing or development).'
    )
    interval_in_hours = forms.ChoiceField(
        choices=models.SparkJob.INTERVAL_CHOICES,
        widget=forms.Select(
            attrs={
                'class': 'form-control',
                'required': 'required',
            }
        ),
        label='Job interval',
        help_text='Interval at which the Spark job should be run',
    )
    job_timeout = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=24,
        label='Job timeout',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'min': '1',
            'max': '24',
        }),
        help_text='Number of hours that a single run of the job can run '
                  'for before timing out and being terminated.'
    )
    start_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(
            attrs={
                'class': 'form-control datetimepicker',
            }),
        label='Job start date',
        help_text='Date and time on which to enable the scheduled Spark job.',
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker',
        }),
        label='Job end date (optional)',
        help_text='Date and time on which to disable the scheduled Spark job '
                  '- leave this blank if the job should not be disabled.',
    )

    class Meta:
        model = models.SparkJob
        fields = []


class NewSparkJobForm(BaseSparkJobForm):
    notebook = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'required': 'required'}),
        label='Analysis Jupyter Notebook',
        help_text='A Jupyter (formally IPython) Notebook has the file extension .ipynb'
    )

    def save(self):
        # create the model without committing, since we haven't
        # set the required created_by field yet
        spark_job = super(NewSparkJobForm, self).save(commit=False)

        # set the field to the user that created the scheduled Spark job
        spark_job.created_by = self.created_by

        # actually save the scheduled Spark job, and return the model object
        spark_job.save(self.cleaned_data['notebook'])
        return spark_job

    class Meta(BaseSparkJobForm.Meta):
        fields = [
            'identifier', 'notebook', 'result_visibility', 'size',
            'interval_in_hours', 'job_timeout', 'start_date', 'end_date'
        ]


class EditSparkJobForm(BaseSparkJobForm):

    class Meta(BaseSparkJobForm.Meta):
        fields = [
            'identifier', 'result_visibility', 'size', 'interval_in_hours',
            'job_timeout', 'start_date', 'end_date'
        ]


class DeleteSparkJobForm(CreatedByFormMixin, forms.ModelForm):
    confirmation = forms.RegexField(
        required=True,
        label='Confirm termination with Spark job identifier',
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
        }),
    )

    def clean_confirmation(self):
        confirmation = self.cleaned_data.get('confirmation')
        if confirmation != self.instance.identifier:
            raise forms.ValidationError(
                "Entered Spark job identifier doesn't match"
            )
        return confirmation

    class Meta:
        model = models.SparkJob
        fields = []
