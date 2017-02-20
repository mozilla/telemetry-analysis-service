from django.db import connections, DatabaseError, InterfaceError
from rq_retry import RetryWorker


class ConnectionClosingRetryWorker(RetryWorker):
    def close_database(self):
        for connection in connections.all():
            try:
                connection.close()
            except InterfaceError:
                pass
            except DatabaseError as exc:
                str_exc = str(exc)
                if 'closed' not in str_exc and 'not connected' not in str_exc:
                    raise

    def perform_job(self, *args, **kwargs):
        self.close_database()
        try:
            return super().perform_job(*args, **kwargs)
        finally:
            self.close_database()

    def work(self, *args, **kwargs):
        self.close_database()
        return super().work(*args, **kwargs)
