### 2017.5.5

#### Spark jobs run history

For every scheduled Spark job you can now see the history of previous
runs on the detail page in the "Runs" tab.

#### More accurate timestamps

For both on-demand clusters as well as scheduled Spark jobs we now
record more details about the start, ready and finish time of the
AWS EMR clusters. The timestamps are shown both on the dashboard as
well as the cluster and Spark job detail pages.

### 2017.5.2

#### Site-wide announcements

Occasionally we may want to inform you about the current **operational status**
of the Telemetry Analysis Service and will do so now using site-wide
announcements at the top of every page.

For example in case we're facing partial degredation of service due to problems
with upstream providers we'll post an update.

#### Run your scheduled Spark jobs right now

Every scheduled Spark job is now able to be run individually out-of-schedule
with the **new "Run now" button** at the top of the Spark job detail page.

To prevent data loss by jobs that are run repeatedly we will skip the next
scheduled run in case it hasn't finished by the scheduled time. Please make
sure to plan accordingly. The Spark job detail page lists the time of the
next run.

#### New unique identifiers for clusters

When creating new on-demand clusters or scheduling new Spark jobs we're now
providing  random and unique identifiers for better operational monitoring.
They can of course still be overridden with custom names.

### 2017.5.1

#### Visual indicators for Spark job cluster status

We now show visual indicators for the current status of the cluster of
scheduled Spark jobs on the dashboard and the detail page.

### 2017.4.3

#### Added ability to define and extend cluster lifetime

<div class="alert alert-warning">
    <h4>Backward-incompatible change!</h4>
    Please note that running clusters are not affected, only new ones.
</div>

On-demand Spark clusters have a new default **lifetime of 8 hours**.

You can **increase the lifetime to 24 hours** using the new optional
**Lifetime** form field when launching a Spark cluster.

Additionally you can **extend the lifetime of a running cluster** with the
`Extend` button on the cluster detail page (next to `Terminate now` button).

The cluster expiration emails will also contain a link to extend the
cluster if needed.

#### Experimental and deprecated EMR releases

When launching an on-demand Spark cluster or scheduling a Spark job, please
be aware that some EMR releases may in the future be marked as **experimental**
or **deprecated** to better explain the expectations around the support we can
provide for those.

In case of a **deprecated** EMR release we'll announce a expected deprecation
window for the version here and on the appropriate mailing lists.

**Experimental** EMR releases are marked as such to be able to vet them in
production. They are available as any other release but are not recommended
for critical Spark clusters or scheduled jobs.

#### New email notifications for expired and timed out Spark jobs

When a scheduled Spark job has expired we'll send out an email notifiying the
owner of it. They may un-expire it by updating the end date of the Spark job
again.

When a Spark job has timed out because it ran longer than the configured
timeout period (up to 24 hours) we will terminate the Spark job and send
an email to the owner requesting to modify the job to run less than the
timeout, e.g. by increasing the number of cluster nodes, improving the Spark
job notebook code etc.

### 2017.3.7

#### All Spark jobs visible for maintainers

Users who are members of the "Spark job maintainers" permission group
can now optionally see the Spark jobs of all users in the dashboard.

### 2017.3.2

#### Persistent cluster storage

Good news everyone - files are now persisted between clusters!
In fact, make changes to your own dotfiles in your home dir -
they will live on between clusters as well.

We will be limiting your home directory size to 20GB, so don't go
saving those big honkin' parquet files.

#### EMR 4.5.0 release removed

The EMR 4.5.0 release was removed and won't be available for new
on-demand clusters and scheduled Spark jobs.

#### Email alerts on scheduled jobs failures

When ATMO discovers that a scheduled job resulted in a failed
cluster state the creator of the scheduled job will receive an
email alerting them of the situation.

#### New out-of-date notifications

The previous automatic page refresher that was active on the
dashboard, the cluster and job detail pages has been replaced by
an in-page-notification when the page has changed, e.g. when a
cluster status is changed on AWS.
