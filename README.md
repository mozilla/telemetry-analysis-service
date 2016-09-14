atmo
====

[![Build Status](https://travis-ci.org/mozilla/telemetry-analysis-service.svg?branch=master)](https://travis-ci.org/mozilla/telemetry-analysis-service)

[![Coverage status](https://img.shields.io/coveralls/mozilla/telemetry-analysis-service/master.svg)](https://coveralls.io/r/mozilla/telemetry-analysis-service)

Run the tests
-------------

There's a sample test in `atmo/base/tests.py` for your convenience, that you can run using the following command:

    docker-compose run web ./manage.py collectstatic # this is only necessary after adding/removing/editing static files
    docker-compose run web ./manage.py test

If you want to run the full suite, with flake8 and coverage, you may use
[tox](https://testrun.org/tox/latest/). This will run the tests the same way
they are run by [travis](https://travis-ci.org)):

    pip install tox
    tox

The `.travis.yml` file will also run [coveralls](https://coveralls.io) by
default.

If you want to benefit from Travis and Coveralls, you will need to activate
them both for your project.

Oh, and you might want to change the "Build Status" and "Coverage Status" links
at the top of this file to point to your own travis and coveralls accounts.

Development Setup
-----------------

This application is packaged with Docker, which manages and maintains a consistent application environment.

On a Debian-derived Linux distributions, run `./bin/build-deb.sh` to perform all
the installation steps automatically. On other OSs, [install Docker](https://docs.docker.com/mac/) and
[Docker Compose](https://docs.docker.com/compose/install/) manually.

To start the application, run `docker-compose up`.

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
    * Run `docker-compose run web ./manage.py migrate --run-syncdb` to update it.
* Django gives some other form of `OperationalError`, and we don't really care about the data that's already in the database (e.g., while developing or testing)
    * Most database issues can be resolved by just deleting the database, `telemetry_analysis.db`. It will be recreated on the next run.
* Database errors are usually caused by an improper database configuration. For development purposes, recreating the database will often solve the issue.
* Django gives an error message similar to `'NoneType' object has no attribute 'get_frozen_credentials'`.
    * The AWS credentials on the current machine are likely not correctly set.
    * Set them in your **ENVIRONMENT VARIABLES** (these environment variables are transferred to the docker container, from definitions in `docker-compose.yml`).
    * See the [relevant section of the Boto3 docs](https://boto3.readthedocs.org/en/latest/guide/configuration.html#environment-variables) for more details.

Production Setup
----------------

1. Add your project in [Docker Registry](https://registry.hub.docker.com/) as [Automated Build](http://docs.docker.com/docker-hub/builds/)
2. Prepare a 'env' file with all the variables needed by dev, stage or production.
3. Run the image:

    docker run --env-file env -p 80:8000 mozilla/atmo

Heroku Setup
------------
1. heroku create
2. heroku config:set DEBUG=False ALLOWED_HOSTS=<foobar>.herokuapp.com, SECRET_KEY=something_secret
   DATABASE_URL gets populated by heroku once you setup a database.
3. git push heroku master

NewRelic Monitoring
-------------------

A newrelic.ini file is already included. To enable NewRelic monitoring
add two enviroment variables:

 - NEW_RELIC_LICENSE_KEY
 - NEW_RELIC_APP_NAME

See the [full list of supported environment variables](https://docs.newrelic.com/docs/agents/python-agent/installation-configuration/python-agent-configuration#environment-variables).
