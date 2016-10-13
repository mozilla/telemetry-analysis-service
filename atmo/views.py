# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .clusters.models import Cluster
from .jobs.models import SparkJob


logger = logging.getLogger("django")


@login_required
def dashboard(request):
    clusters = (Cluster.objects.filter(created_by=request.user)
                               .filter(end_date__gt=timezone.now() - timedelta(days=1))
                               .order_by("-start_date"))
    jobs = SparkJob.objects.filter(created_by=request.user).order_by("start_date")
    context = {
        'active_clusters': clusters,
        'user_spark_jobs': jobs,
    }
    return render(request, 'atmo/dashboard.html', context=context)
