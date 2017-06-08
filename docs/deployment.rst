Deployment
==========

Heroku Setup
------------

#. Run ``heroku create``.

#. Add Heroku Postgres and Redis hobby add-ons.

#. Set the appropriate config variables, e.g.:

   .. code-block:: console

    heroku config:set \
        DJANGO_DEBUG=False \
        DJANGO_ALLOWED_HOSTS="<foobar>.herokuapp.com," \
        DJANGO_SECRET_KEY=something_secret

   ..where ``<foobar>`` is the name of your Heroku app you created in step 1.
   ``DATABASE_URL`` and ``REDIS_URL`` gets populated by Heroku once you
   setup a database.

#. Run this since we're using multiple Heroku buildpacks (see ``.buildpacks``):

   .. code-block:: console

    heroku buildpacks:set https://github.com/heroku/heroku-buildpack-multi.git

#. Push branch to GitHub with ``git push origin``

NewRelic Monitoring
-------------------

A ``newrelic.ini`` file is already included. To enable NewRelic monitoring
add two enviroment variables:

* ``NEW_RELIC_APP_NAME``
* ``NEW_RELIC_CONFIG_FILE`` to ``/app/newrelic.ini``
* ``NEW_RELIC_ENVIRONMENT`` to either ``staging`` or ``production``
* ``NEW_RELIC_LICENSE_KEY``
* ``NEW_RELIC_LOG`` to ``stdout``

See the `full list of environment variables`_ supported by Newrelic.

.. _`full list of environment variables`: https://docs.newrelic.com/docs/agents/python-agent/installation-configuration/python-agent-configuration#environment-variables
