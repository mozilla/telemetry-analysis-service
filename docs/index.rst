Mozilla ATMO
============

Welcome to the documentation of **ATMO**, the code that runs Mozilla_'s
`Telementry Analysis Service`_.

ATMO is a self-service portal to launch on-demand `AWS EMR`_ clusters with
`Apache Spark`_, `Apache Zeppelin`_ and Jupyter_ installed.
Additionally it allows to schedule Spark jobs to run regularly based on
uploaded Jupyter (and soon Zeppelin) notebooks.

It provides a management UI for public SSH keys when launching on-demand
clusters, login via Google auth and flexible adminstration interfaces for
users and admins.

Behind the scenes it's shipped as Docker_ images and uses Python_ 3.6 for
the web UI (Django_) and the task management (Celery_).

.. _`Mozilla`: https://www.mozilla.org/
.. _`Telementry Analysis Service`: https://analysis.telemetry.mozilla.org/
.. _`AWS EMR`: https://aws.amazon.com/emr/
.. _`Apache Spark`: https://spark.apache.org/
.. _`Apache Zeppelin`: https://zeppelin.apache.org/
.. _`Jupyter`: https://jupyter.org/
.. _Docker: https://www.docker.com/
.. _Python: https://python.org/
.. _Django: https://www.djangoproject.com/
.. _Celery: https://www.celeryproject.org/

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   workflows
   maintenance
   development
   deployment
   reference/index
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
