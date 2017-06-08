Development
===========

ATMO is maintained on GitHub in its own repository at:

  https://github.com/mozilla/telemetry-analysis-service

Please clone the Git repository using the git command line tool
or any other way you're comfortable with, e.g.:

.. code-block:: console

  git clone https://github.com/mozilla/telemetry-analysis-service

ATMO also uses Docker for local development and deployment.
Please make sure to install `Docker`_ and `Docker Compose`_ on your
computer to contribute code or documentation changes.

Configuration
-------------

To set the application up, please copy the ``.env-dist`` file to one named
``.env`` and then update the variables starting with ``AWS_`` with the
appropriate value.

Set the ``DJANGO_SECRET_KEY`` variable using the output of the following
command:

.. code-block:: console

    python -c "import secrets; print(secrets.token_urlsafe(50))"

To start the application, run:

.. code-block:: console

    make up

.. _`Docker`: https://docs.docker.com/engine/installation/#supported-platforms
.. _`Docker Compose`: https://docs.docker.com/compose/install/

Run the tests
-------------

There's a sample test in ``tests/test_users.py`` for your convenience,
that you can run using the following command on your computer:

.. code-block:: console

    make test

This will spin up a Docker container to run the tests, so please set up
the development setup first.

The default options for running the test are in ``pytest.ini``. This is a
good set of defaults.

Alternatively, e.g. when you want to only run part of the tests first
open a console to the web container..

.. code-block:: console

   make shell

and then run pytest directly:

.. code-block:: console

   pytest

Some helpful command line arguments to pytest (won't work on ``make test``):

``--pdb``:
  Drop into pdb on test failure.

``--create-db``:
  Create a new test database.

``--showlocals``:
  Shows local variables in tracebacks on errors.

``--exitfirst``:
  Exits on the first failure.

``--lf, --last-failed``:
  Run only the last failed tests.

See ``pytest --help`` for more arguments.

.. _tests:

Running subsets of tests and specific tests
```````````````````````````````````````````

There are a bunch of ways to specify a subset of tests to run:

* all the tests that have "foobar" in their names::

    pytest -k foobar

* all the tests that don't have "foobar" in their names::

    pytest -k "not foobar"

* tests in a certain directory::

    pytest tests/jobs/

* specific test::

    pytest tests/jobs/test_views.py::test_new_spark_job

See http://pytest.org/latest/usage.html for more examples.

Troubleshooting
---------------

Docker-Compose gives an error message similar to "ERROR: client and server
don't have same version (client : 1.21, server: 1.18)"

  Make sure to install the latest versions of both Docker and Docker-Compose.
  The current versions of these in the Debian repositories might not be mutually compatible.

Django gives an error message similar to ``OperationalError: SOME_TABLE does not exist``

  The database likely isn't set up correctly. Run ``make migrate`` to update it.

Django gives some other form of ``OperationalError``, and we don't really
care about the data that's already in the database (e.g., while developing or
testing)

  Database errors are usually caused by an improper database configuration. For development purposes, recreating the database will often solve the issue.

Django gives an error message similar to ``'NoneType' object has no attribute
'get_frozen_credentials'``.

  * The AWS credentials on the current machine are likely not correctly set.

  * Set them in your **ENVIRONMENT VARIABLES** (these environment variables are
    transferred to the docker container, from definitions in ``.env``).

  * See the [relevant section of the Boto3 docs](https://boto3.readthedocs.org/en/latest/guide/configuration.html#environment-variables) for more details.

Django raises a 404 when trying to login

  * Google Developer credentials are needed to get the Google authentication workflow running.

  * Go to [console.developers.google.com](https://console.developers.google.com/), create a new project

  * Click on "credentials" and create a new "OAuth client ID"

    * Application type: "Web application"

    * Name: ATMO (e.g. append "dev" or similar for local development)

    * Authorized redirect URIs:

      ``<protocol>://<hostname>[:<port>]/accounts/google/login/callback/``
      (e.g.: ``http://localhost:8000/accounts/google/login/callback/`` for
      local development)

    * With the client ID and client secret run the following to add them to
      the django-allauth config system:

      .. code-block:: console

        make shell

      Then add the credentials to the database:

      .. code-block:: console

        ./manage.py add_google_credentials --client-id=CLIENT_ID --client-secret=CLIENT_SECRET
