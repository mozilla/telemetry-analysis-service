web: newrelic-admin run-program gunicorn atmo.wsgi:application --workers 4 --log-file -
worker: newrelic-admin run-program python manage.py rqworker --worker-class=rq.SimpleWorker default
# django-rq doesn't support rqscheduler retry mode yet
# so we need to use the original startup script
scheduler: newrelic-admin run-program rqscheduler --url=$REDIS_URL

release: ./bin/pre_deploy
