web: bin/start-stunnel bin/run web
worker: bin/start-stunnel bin/run worker
# django-rq doesn't support rqscheduler retry mode yet
# so we need to use the original startup script
scheduler: bin/start-stunnel bin/run scheduler
release: bin/pre_deploy
