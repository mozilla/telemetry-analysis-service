Changelog
=========

Welcome to the running release notes of ATMO!

- You can use this document to see high-level changes done in each release
  that is git tagged.

- Backward-incompatible changes or other notable events that have an
  impact on users are noted individually.

- The order of this changelog is descending (newest first).

- Dependency updates are only mentioned when they require user attention.

2017.6.0
--------

:date: 2017-06-06

Add Zeppelin examples to cluster detail

2017.5.7
--------

:date: 2017-05-30

Fix regression introduced when the backoff feature for task retries was
improved in 2017.5.5.

2017.5.[5,6]
------------

:date: 2017-05-24

Fix more race conditions in sending out emails.

Fix duplicate job runs due to job scheduling race conditions.

Store and show datetimes from EMR status updates for better monitoring.

Add job history details to job detail page.

Improved backoff patterns by inlining the Celery task retries.

2017.5.[3,4]
------------

:date: 2017-05-18

Fix issue with Celery monitoring.

2017.5.2
--------

:date: 2017-05-17

Fix race conditions in email sending.

Add ability to run job right now.

UI fixes to the cluster and Spark job detail pages.

Upgrade to Django 1.11 and Python 3.6.

Add a responsive admin theme.

Add ability to show a site-wide announcement on top of every page.

Update the status of all past Spark job runs not only the last one.

Better unique cluster identifiers based on scientist names.

2017.5.1
--------

:date: 2017-05-11

Add status and visual indicators to scheduled Spark jobs listings.

Fix issue with running scheduled Celery tasks multiple times.

2017.5.0
--------

:date: 2017-05-03

Use user part of email addresses as username (e.g. "jdoe" in
"jdoe@mozilla.com) instead of first name.

Add Celery monitoring to Django admin.

2017.4.3
--------

:date: 2017-04-27

UX updates to job detail page.

Minor fixes for Celery schedule refactoring.

2017.4.2
--------

:date: 2017-04-26

Updated Celery timeout.

Populate new Celery schedules for all scheduled Spark jobs.

2017.4.1
--------

:date: 2017-04-25

Add a Celery task for running a Spark job.

This task is used of Redbeat to schedule the Spark jobs using the Celery beat.
We add/remove Spark jobs from the schedule on save/delete and can restore the
schedule from the database again.

Send emails for Spark jobs when expired and when they have timed out and need
to be modified.

Refactored and extended tests.

2017.4.0
--------

:date: 2017-04-04

Moved EMR releases into own data model for easy maintenance (including
deprecation and experimental tags).

Add ability to define a lifetime on cluster start.

Change default lifetime to 8 hours (~a work day), maximum stays at 24 hours.

Add ability to extend the lifetime of clusters on demand. The cluster expiration
email will notify cluster owners about that ability, too.

2017.3.[6,7]
------------

:date: 2017-03-28/2017-03-29

Show all scheduled Spark jobs for admin users in the Spark job maintainers
group.

Fix logging for Celery and RedBeat.

2017.3.5
--------

:date: 2017-03-22

Switch to Celery as task queue to improve stability and processing guarentees.

Wrap more tasks in Django database transactions to reduce risk of race conditions.

Only updates the cluster master address if the cluster isn't ready.

Pins Node dependencies and use Greenkeeper for dependency CI.

2017.3.4
--------

:date: 2017-03-20

Fixing an inconsistency with how the run alert status message is stored
with values from Amazon, extending the length of the column.

Check and run jobs only every 5 minutes instead of every minute to reduce
API access numbers.

2017.3.3
--------

:date: 2017-03-17

Regression fixes to the email alerting feature introduced in 2017.3.2
that prevented scheduled jobs to run successfully.

2017.3.2
--------

:date: 2017-03-15

BACKWARD INCOMPATIBLE: Removes EMR release 4.5.0.

BACKWARD INCOMPATIBLE: Make clusters persist the home directory between runs.

Adds a changelog (this file) and a "What's new?" section (in the footer).

Adds email alerting if a scheduled Spark job fails.

Replaced automatic page refresher with in-page-alerts when page changes on server.

Moved project board to Waffle: https://waffle.io/mozilla/telemetry-analysis-service

Run flake8 automatically as part of test suite.

2017.3.[0,1]
------------

:date: 2017-03-07/2017-03-08

Selects the SSH key automatically if only one is present.

Uses ListCluster API endpoint for updating Spark job run states
instead of DescribeCluster to counteract AWS API throtteling.

2017.2.[9,10,11,12,13]
----------------------

:date: 2017-02-23

Regression fixes for the Python 3 migration and Zeppeling integration.

2017.2.[6,7,8]
--------------

:date: 2017-02-20/2017-02-21

Adds the ability to store the history of scheduled Spark job for
planned features such as alerting and cost calculations.

2017.2.[4,5]
------------

:date: 2017-02-17

Adds experimental support for Apache Zeppelin, next to Jupyter a second
way to manage notebooks.

Improves client side form validation dramaticlly and changes file selector
to better suited system.

Adds exponential backoff retries for the worker system to counteract
AWS API throtteling for jobs that update cluster status or run scheduled
Spark jobs.

Moves from Python 2 to 3.

2017.2.[1,2,3]
--------------

:date: 2017-02-07/2017-02-10

Uses AWS EC2 spot instances for scheduled Spark jobs with more than one
node.

Moves issue management from Bugzilla to `GitHub <https://github.com/mozilla/telemetry-analysis-service/issues>`_.

2017.1.[11,12]
--------------

:date: 2017-01-31

Self-dogfoods the newly implemented `python-dockerflow <https://python-dockerflow.rtfd.io/>`_.

Fix many UX issues in the various forms.

2017.1.[7,8,9,10]
-----------------

:date: 2017-01-24

Adds ability to upload personal SSH keys to simplify starting clusters.

Adds a new required description field to Spark job to be able to debug
jobs easily.

Adds EMR 5.2.1 to list of available EMR versions.

Uses new shared public SSH key that is used by the hadoop user on EMR.

2017.1.[0,1,2,3,4,5,6]
----------------------

:date: 2017-01-20

First release of 2017 that comes with a lot of changes around
deployment, UI and UX. \o/

Adopts NPM as a way to maintain frontend dependencies.

Adds a object level permission system to be able to share CRUD
permissions per user or user group, e.g. admins can see clusters
and Spark jobs of other users now.

Makes the cluster and Spark job deletion confirmation happen in
place instead of redirecting to separate page that asks for confirmation.

Extends tests and adds test coverage reporting via Codecov.

Drops Travis-CI in favor of Circle CI.

Allows enabling/disabling AWS EC2 spot instances via the Django admin UI
in the Constance section.

2016.11.5
---------

:date: 2016-11-21

Fix job creation edge case.

More NewRelic fixes.

2016.11.[2,3,4]
---------------

:date: 2016-11-17

Fixes logging related to Dockerflow.

Turned off NewRelic's "high_security" mode.

Increases the job timeouts for less job kills.

Removes the need for Newrelic deploys to Heroku.

2016.11.1
---------

:date: 2016-11-14

Implements Dockerflow health checks so it follows the best
practices of Mozilla's
`Dockerflow <https://github.com/mozilla-services/Dockerflow>`_.
Many thanks to @mythmon for the inspiration in the Normandy code.

2016.11.0
---------

:date: 2016-11-11

The first release of ATMO V2 under the new release system that ports
the majority of the V1 to a new codebase.

This is a major milestone after months of work of many contributors,
finishing the work of Mozilla community members and staff.
