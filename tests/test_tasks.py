import pytest

from atmo.celery import celery


@celery.task(bind=True, iterations=0, max_retries=5)
@celery.autoretry(exception=(ZeroDivisionError,))
def autoretry_task(self, a, b):
    self.iterations += 1
    return a / b


def test_autoretry():
    with pytest.raises(ZeroDivisionError):
        autoretry_task.apply(args=(1, 0,)).get()
    # the number of calls the plus the max retries
    assert autoretry_task.iterations == autoretry_task.max_retries + 1
