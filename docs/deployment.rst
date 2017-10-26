Deployment
==========

Releasing ATMO happens by tagging a CalVer_ based Git tag with the following
pattern:

    YYYY.M.N

``YYYY`` is the four-digit year number, ``M`` is a single-digit month number
and ``N`` is a single-digit zero-based counter which does not relate to the
day of the release. Valid versions numbers are:

- 2017.10.0

- 2018.1.0

- 2018.12.12

- 1970.1.1



Once the Git tag has been pushed to the main GitHub repository using
``git push origin --tags``, Circle CI will automatically build a tagged
Docker image after the tests have passed and push it to Docker Hub.
From there the Mozilla CloudOPs team has configured a stage/prod deployment
pipeline.

Stage deployments happen automatically when a new release is made.
Prod deployments happen on demand by the CloudOPs team.

.. _CalVer: http://calver.org/
