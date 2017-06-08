Workflows
=========

There are a few workflows in the ATMO code base that are of interest and
decide how it works:

- Adding SSH keys

- Creating an on-demand cluster

- Scheduling a Spark job


Adding SSH keys
---------------



Creating an on-demand cluster
-----------------------------


Scheduling a Spark job
----------------------

.. graphviz::

   digraph runjob {
       job [label="Run job task"];
       getrun [shape=diamond, label="Get run"];
       hasrun [shape=diamond, label="Has Run?"];
       logandreturn [shape=box, label="Log and return"];
       isenabled [shape=diamond, label="Is enabled?"];
       sync [shape=box, label="Sync run"];
       isrunnable [shape=diamond, label="Is runnable?"];
       hastimedout [shape=diamond, label="Timed out?"];
       isdue [shape=diamond, label="Is due?"];
       retryin10mins [shape=box, label="Retry in 10 mins"];
       notifyowner [shape=box, label="Notify owner" ];
       terminatejob [shape=box, label="Terminate last run" ];
       unschedule_and_expire [shape=box, label="Unschedule and expire" ];
       provisioncluster [shape=box, label="Provision cluster" ];

       job -> getrun;
       getrun -> hasrun [label="FOUND"];
       getrun -> logandreturn [label="NOT FOUND"];
       hasrun -> isenabled [label="NO"];
       hasrun -> sync [label="YES"];
       sync -> isenabled;
       isenabled -> logandreturn [label="NO"];
       isenabled -> isrunnable [label="YES"];
       isrunnable -> hastimedout [label="NO"];
       isrunnable -> isdue [label="YES"];
       hastimedout -> retryin10mins [ label="NO" ];
       hastimedout -> notifyowner [ label="YES" ];
       notifyowner -> terminatejob [ label="Job ABC timed out too early..."];
       isdue -> unschedule_and_expire [ label="NO" ];
       isdue -> provisioncluster [ label="YES" ];
   }
