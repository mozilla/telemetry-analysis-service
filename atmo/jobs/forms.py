from django import forms

from . import models


class NewSparkJobForm(forms.ModelForm):
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
            'data-content': 'A brief description of the scheduled Spark job\'s purpose, '
                            'visible in the AWS management console.',
            'data-validation-pattern-message': 'Valid job names are strings of alphanumeric '
                                               'characters, \'_\', and \'-\'.',
        })
    )
    notebook = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'required': 'required'})
    )
    result_visibility = forms.ChoiceField(
        choices=[
            ('private', 'Private: results output to an S3 bucket, viewable with AWS credentials'),
            ('public', 'Public: results output to a public S3 bucket, viewable by anyone'),
        ],
        widget=forms.Select(
            attrs={'class': 'form-control', 'required': 'required'}
        )
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
            'data-content': 'Number of workers to use when running the Spark job '
                            '(1 is recommended for testing or development).',
        })
    )
    interval_in_hours = forms.ChoiceField(
        choices=[
            (24, "Daily"),
            (24 * 7, "Weekly"),
            (24 * 30, "Monthly"),
        ],
        widget=forms.Select(
            attrs={'class': 'form-control', 'required': 'required'}
        )
    )
    job_timeout = forms.IntegerField(
        required=True,
        min_value=1, max_value=24,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'min': '1', 'max': '24',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Number of hours that a single run of the job can run '
                            'for before timing out and being terminated.',
        })
    )
    start_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Date/time on which to enable the scheduled Spark job.',
        })
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Date/time on which to disable the scheduled Spark job '
                            '- leave this blank if the job should not be disabled.',
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(NewSparkJobForm, self).__init__(*args, **kwargs)

    def save(self):
        # create the model without committing, since we haven't
        # set the required created_by field yet
        new_spark_job = super(NewSparkJobForm, self).save(commit=False)

        # set the field to the user that created the scheduled Spark job
        new_spark_job.created_by = self.created_by

        # actually save the scheduled Spark job, and return the model object
        new_spark_job.save(self.cleaned_data["notebook"])

    class Meta:
        model = models.SparkJob
        fields = [
            'identifier', 'result_visibility', 'size', 'interval_in_hours',
            'job_timeout', 'start_date', 'end_date'
        ]


class EditSparkJobForm(forms.ModelForm):
    job = forms.ModelChoiceField(
        queryset=models.SparkJob.objects.all(),
        required=True,
        widget=forms.HiddenInput(attrs={
            # fields with the `selected-spark-job` class get their value
            # automatically set to the job ID of the selected scheduled Spark job
            'class': 'selected-spark-job',
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
            'data-content': 'A brief description of the scheduled Spark job\'s purpose, '
                            'visible in the AWS management console.',
            'data-validation-pattern-message': 'Valid job names are strings of alphanumeric '
                                               'characters, \'_\', and \'-\'.',
        })
    )
    result_visibility = forms.ChoiceField(
        choices=[
            ('private', 'Private: results output to an S3 bucket, viewable with AWS credentials'),
            ('public', 'Public: results output to a public S3 bucket, viewable by anyone'),
        ],
        widget=forms.Select(
            attrs={'class': 'form-control', 'required': 'required'}
        )
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
            'data-content': 'Number of workers to use when running the Spark job '
                            '(1 is recommended for testing or development).',
        })
    )
    interval_in_hours = forms.ChoiceField(
        choices=[
            (24, "Daily"),
            (24 * 7, "Weekly"),
            (24 * 30, "Monthly"),
        ],
        widget=forms.Select(
            attrs={'class': 'form-control', 'required': 'required'}
        )
    )
    job_timeout = forms.IntegerField(
        required=True,
        min_value=1, max_value=24,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'min': '1', 'max': '24',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Number of hours that a single run of the job can run '
                            'for before timing out and being terminated.',
        })
    )
    start_date = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Date/time on which to enable the scheduled Spark job.',
        })
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker',
            'data-toggle': 'popover',
            'data-trigger': 'focus',
            'data-placement': 'top',
            'data-container': 'body',
            'data-content': 'Date/time on which to disable the scheduled Spark job '
                            '- leave this blank if the job should not be disabled.',
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(EditSparkJobForm, self).__init__(*args, **kwargs)

    def save(self):
        cleaned_data = super(EditSparkJobForm, self).clean()
        job = cleaned_data["job"]
        if self.created_by != job.created_by:  # only allow editing jobs that one creates
            raise ValueError("Disallowed attempt to edit another user's scheduled job")
        job.identifier = cleaned_data["identifier"]
        job.result_visibility = cleaned_data["result_visibility"]
        job.size = cleaned_data["size"]
        job.interval_in_hours = cleaned_data["interval_in_hours"]
        job.job_timeout = cleaned_data["job_timeout"]
        job.start_date = cleaned_data["start_date"]
        job.end_date = cleaned_data["end_date"]
        job.save()

    class Meta:
        model = models.SparkJob
        fields = [
            'identifier', 'result_visibility', 'size', 'interval_in_hours',
            'job_timeout', 'start_date', 'end_date'
        ]


class DeleteSparkJobForm(forms.ModelForm):
    job = forms.ModelChoiceField(
        queryset=models.SparkJob.objects.all(),
        required=True,
        widget=forms.HiddenInput(attrs={
            # fields with the `selected-spark-job` class get their value
            # automatically set to the job ID of the selected scheduled Spark job
            'class': 'selected-spark-job',
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(DeleteSparkJobForm, self).__init__(*args, **kwargs)

    def save(self):
        cleaned_data = super(DeleteSparkJobForm, self).clean()
        job = cleaned_data["job"]
        if self.created_by != job.created_by:  # only allow deleting jobs that one creates
            raise ValueError("Disallowed attempt to delete another user's scheduled job")
        job.delete()

    class Meta:
        model = models.SparkJob
        fields = []
