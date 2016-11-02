# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.middleware import NewRelicPapertrailMiddleware


def test_newrelic_papertrail(mocker, monkeypatch, rf):
    add_custom_parameter = mocker.patch('newrelic.agent.add_custom_parameter')

    request = rf.get('/')
    result = NewRelicPapertrailMiddleware().process_request(request)
    assert result is None
    assert add_custom_parameter.call_count == 0

    monkeypatch.setenv('HEROKU_APP_NAME', 'atmo-dev')
    middleware = NewRelicPapertrailMiddleware()
    assert middleware.heroku_app_name == 'atmo-dev'
    result = middleware.process_request(request)
    param_name, param_value = add_custom_parameter.call_args[0]
    assert 'log_url' == param_name
    assert ('https://papertrailapp.com/systems/atmo-dev/events?time=' in
            param_value)
