### 2017.3.2

#### Persistent cluster storage

Please be aware that the Spark clusters are now **persisting
the home directory between launches**. Caution is advised with
regard to long running scripts that write to disk, especially
with regard to write speed and volume size.

#### Automatic page refresher removed

The automatic page refresher that was active on the dashboard
and the cluster and job detail pages has been removed to prevent
unneeded client side memory consumption when having many ATMO
URLs open in tabs at the same time. Just refresh the page manually
instead.
