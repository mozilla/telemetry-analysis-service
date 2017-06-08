===========
Maintenance
===========

EMR releases
============

Dependency upgrades
===================

ATMO uses a number of dependencies for both the backend as well as the
frontend web UI.

For the first we're using `pip requirements.txt`_ files to manage dependencies,
whose version should always be pinned to an exact version and have hashes
attached for the individual release files for pip's `hash-checking mode`_.

For the frontend dependencies we're using NPM_'s default ``package.json`` and
NPM >= 5's ``package-lock.json``.

See below for guides to update both.

.. _`pip requirements.txt`: https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format
.. _NPM: https://www.npmjs.com/get-npm

Python dependencies
-------------------

Python dependencies are installed using pip during the Docker image build
process. As soon as you build the docker image using ``make build`` it'll
check if the appropriate requirements file has changed and rebuilds the
container image if needed.

To add a new Python dependency please:

* Log in into the web container with ``make shell``.

* Change into the requirements folder with ``cd /app/requirements``

* Then, depending on the area in which the dependency you're about to
  add/update, chose one of the following files to update:

  * ``build.txt`` - dependencies for when the Docker image is built, the
    default requirements file, basically.

  * ``docs.txt`` - dependencies for building the Sphinx based docs.

  * ``tests.txt`` - dependencies for running the :ref:`test suite <tests>`.

* Add/update the dependency in the file you chose, including a hash for pip's
  `hash-checking mode`_. You may want to use the tool `hashin`_ to do that,
  e.g. ``hashin -r /app/requirements/docs.txt Sphinx``.

* Leave the container again with ``exit``.

* Run ``make build`` on the host machine.

That will rebuild the images used by docker-compose.

.. _hashin: https://pypi.python.org/pypi/hashin

NPM ("front-end") dependencies
------------------------------

The front-end dependencies are installed when building the Docker images
just like Python dependencies.

To add a new dependency to ATMO, please:

* Log in into the web container with ``make shell``.

* Install the new dependency with ``npm install --save-exact <name>``

* Delete the temporary ``node_modules`` folder: ``rm -rf /app/node_modules``.

* Leave the container again with ``exit``.

* Run ``make build`` on the host machine

* Extend the ``NPM_FILE_PATTERNS`` setting in the ``settings.py``
  file with the files that are needed to be copied by Django's
  ``collectstatic`` management command.

That will rebuild the images used by docker-compose.

.. _`hash-checking mode`: https://pip.pypa.io/en/stable/reference/pip_install/#hash-checking-mode
