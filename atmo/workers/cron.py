import datetime
import kronos

from .models import Worker


@kronos.register('0 * * * *')
def delete_worker():
    """delete expired workers"""
    now = datetime.now()

    for worker in Worker.objects.all():
        if worker.end_date >= now:  # the worker is expired
            worker.delete()
