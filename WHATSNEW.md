### 2017.3.2

#### Persistent cluster storage

Good news everyone - files are now persisted between clusters!
In fact, make changes to your own dotfiles in your home dir -
they will live on between clusters as well.

We will be limiting your directory size to 20GB, so don't go
saving those big honkin' parquet files.

#### Automatic page refresher removed

The automatic page refresher that was active on the dashboard
and the cluster and job detail pages has been removed to prevent
unneeded client side memory consumption when having many ATMO
URLs open in tabs at the same time. Just refresh the page manually
instead.
