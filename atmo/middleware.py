import time
import os
import newrelic.agent


class NewRelicPapertrailMiddleware(object):

    def __init__(self):
        self.heroku_app_name = os.environ.get('HEROKU_APP_NAME')

    def process_request(self, request):
        if not self.heroku_app_name:
            return
        log_url = ("https://papertrailapp.com/systems/%s/events?time=%d" %
                   (self.heroku_app_name, time.time()))
        newrelic.agent.add_custom_parameter('log_url', log_url)
