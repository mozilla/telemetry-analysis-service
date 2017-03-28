### 2017.3.6

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
