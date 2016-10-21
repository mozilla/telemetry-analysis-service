atmo - The code for the Telemetry Analysis Service
==================================================

[![Build Status](https://travis-ci.org/mozilla/telemetry-analysis-service.svg?branch=master)](https://travis-ci.org/mozilla/telemetry-analysis-service)

[![codecov](https://codecov.io/gh/mozilla/telemetry-analysis-service/branch/master/graph/badge.svg)](https://codecov.io/gh/mozilla/telemetry-analysis-service)

Run the tests
-------------

There's a sample test in `tests/test_users.py` for your convenience,
that you can run using the following command:

    make test

If you want to run the full suite, with flake8 and coverage, you may use
[tox](https://testrun.org/tox/latest/). This will run the tests the same way
they are run by [travis](https://travis-ci.org)):

    pip install tox
    tox

The `.travis.yml` file will also run [codecov](https://codecov.io) by
default.

If you want to benefit from Travis and Codecov, you will need to activate
them both for your project.

Oh, and you might want to change the "Build Status" and "Coverage Status" links
at the top of this file to point to your own travis and codecov accounts.

Development Setup
-----------------

This application uses Docker for local development. Please make sure to
[install Docker](https://docs.docker.com/mac/) and
[Docker Compose](https://docs.docker.com/compose/install/).

To set the application up, please copy the `.env-dist` file to one named `.env`
and then update the variables starting with `AWS_` with the appropriate.

Set the `SECRET_KEY` variable using the output of the following command:

    python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"

To start the application, run `make up`.

Quick troubleshooting guide:

* Docker gives an error message similar to `ERROR: Couldn't connect to Docker daemon at http+docker://localunixsocket - is it running?`
    * Run the command as administrator/superuser (for testing purposes, that is).
    * Make sure the user is in the `docker` group (use the `sudo usermod -aG docker ${USER}` command to do this). This allows the user to use Docker without superuser privileges. Note that this does not take effect until the user logs out and logs in again.

* Docker-Compose gives an error message similar to `ERROR: client and server don't have same version (client : 1.21, server: 1.18)`
    * Make sure to install the latest versions of both Docker and Docker-Compose. The current versions of these in the Debian repositories might not be mutually compatible.

* Docker gives an error message similar to `Err http://security.debian.org jessie/updates InRelease`
    * The installed Docker version is possibly too old. Make sure to use the latest available stable version.
    * Ensure that the DNS configuration is sane: see if `docker-compose run web ping security.debian.org` can connect successfully.

* Django gives an error message similar to `OperationalError: SOME_TABLE doesn't exist`
    * The database likely isn't set up correctly.
    * Run `make migrate` to update it.

* Django gives some other form of `OperationalError`, and we don't really care about the data that's already in the database (e.g., while developing or testing)
    * Most database issues can be resolved by just deleting the database, `telemetry_analysis.db`. It will be recreated on the next run.

* Database errors are usually caused by an improper database configuration. For development purposes, recreating the database will often solve the issue.

* Django gives an error message similar to `'NoneType' object has no attribute 'get_frozen_credentials'`.
    * The AWS credentials on the current machine are likely not correctly set.
    * Set them in your **ENVIRONMENT VARIABLES** (these environment variables are transferred to the docker container, from definitions in `.env`).
    * See the [relevant section of the Boto3 docs](https://boto3.readthedocs.org/en/latest/guide/configuration.html#environment-variables) for more details.

* Django raises a 404 when trying to login
    * Google Developer credentials are needed to get the Google authentication
      workflow running.
    * Go to https://console.developers.google.com/, create a new project
    * Click on "credentials" and create a new "OAuth client ID"
        * Application type: "Web application"
        * Name: "ATMO" (e.g. append "dev" or similar for local development)
        * Authorized redirect URIs:
            * `<protocol>://<hostname>[:<port>]/accounts/google/login/callback/` e.g.:
            * `http://localhost:8000/accounts/google/login/callback/` for local development
    * With the client ID and client secret given run the following to add them
      to the django-allauth config system:
        * `CLIENT_ID=<client-id> CLIENT_SECRET=<client-secret> make creds`

Heroku Setup
------------
1. `heroku create`
2. `heroku config:set DEBUG=False ALLOWED_HOSTS=<foobar>.herokuapp.com, SECRET_KEY=something_secret`
   `DATABASE_URL` gets populated by heroku once you setup a database.
3. Run `heroku buildpacks:set https://github.com/heroku/heroku-buildpack-multi.git` since we're using multiple Heroku buildpacks (see `.buildpacks`)
4. Push branch to GitHub with `git push origin`, Heroku will auto-deploy to staging

NewRelic Monitoring
-------------------

A newrelic.ini file is already included. To enable NewRelic monitoring
add two enviroment variables:

- `NEW_RELIC_API_KEY`
- `NEW_RELIC_APP_NAME`
- `NEW_RELIC_CONFIG_FILE` to `/app/newrelic.ini`
- `NEW_RELIC_ENVIRONMENT` to either `staging` or `production`
- `NEW_RELIC_LICENSE_KEY`
- `NEW_RELIC_LOG` to `stdout`

See the [full list of supported environment variables](https://docs.newrelic.com/docs/agents/python-agent/installation-configuration/python-agent-configuration#environment-variables).
