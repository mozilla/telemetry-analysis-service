from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from ..utils import provisioning


class Worker(models.Model):
    identifier = models.CharField(
        max_length=100,
        help_text="Worker name, used to non-uniqely identify individual workers."
    )
    public_key = models.CharField(
        max_length=100000,
        help_text="Public key that should be authorized for SSH access to the worker."
    )
    start_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the worker was started, or null if the worker isn't started yet."
    )
    end_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the worker will expire and automatically be deleted."
    )
    created_by = models.ForeignKey(
        User, related_name='worker_created_by',
        help_text="User that created the worker instance."
    )
    instance_id = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="AWS EC2 instance ID for the cluster, used for worker management."
    )

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<Worker {}>".format(self.identifier)

    def get_info(self):
        return provisioning.worker_info(self.instance_id)

    def save(self, *args, **kwargs):
        # actually start the worker
        if not self.instance_id:
            self.instance_id = provisioning.worker_start(
                self.created_by.email,
                self.identifier,
                self.public_key
            )

        # set the dates
        if not self.start_date:
            self.start_date = timezone.now()
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=1)  # workers expire after 1 day
        return super(Worker, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        provisioning.worker_stop(self.worker_id)

        return super(Worker, self).delete(*args, **kwargs)
