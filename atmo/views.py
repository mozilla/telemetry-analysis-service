# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .clusters.models import Cluster
from .jobs.models import SparkJob


logger = logging.getLogger("django")


@login_required
def dashboard(request):
    clusters = Cluster.objects.filter(
        created_by=request.user
    ).order_by("-start_date")

    # the cluster filter defaults to active ones
    clusters_filter = request.GET.get('clusters', 'active')

    if clusters_filter == 'active':
        clusters = clusters.exclude(
            most_recent_status__in=Cluster.FINAL_STATUS_LIST,
        )
    elif clusters_filter == 'inactive':
        clusters = clusters.filter(
            most_recent_status__in=Cluster.FINAL_STATUS_LIST,
        )

    jobs = SparkJob.objects.filter(created_by=request.user).order_by("start_date")
    context = {
        'clusters': clusters,
        'clusters_filter': clusters_filter,
        'user_spark_jobs': jobs,
    }
    return render(request, 'atmo/dashboard.html', context=context)
