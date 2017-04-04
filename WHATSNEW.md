### 2017.4.0

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
