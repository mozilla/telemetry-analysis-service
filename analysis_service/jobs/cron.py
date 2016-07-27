import kronos

from .models import SparkJob


@kronos.register('0 * * * *')
def launch_jobs():
    # launch scheduled jobs if necessary
    SparkJob.step_all()
