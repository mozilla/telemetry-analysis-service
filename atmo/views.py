# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import HttpResponseServerError
from django.shortcuts import redirect
from django.template import Context, TemplateDoesNotExist, loader
from django.template.response import TemplateResponse
from django.views.decorators.csrf import requires_csrf_token
from guardian.shortcuts import get_objects_for_group, get_objects_for_user

from .clusters.models import Cluster
from .decorators import modified_date
from .jobs.models import SparkJob


@login_required
@modified_date
def dashboard(request):
    # allowed filters for clusters
    default_cluster_filter = 'active'
    clusters_filters = ['active', 'terminated', 'failed', 'all']

    # the cluster filter defaults to active ones
    clusters_shown = request.GET.get('clusters', default_cluster_filter)
    if clusters_shown not in clusters_filters:
        clusters_shown = default_cluster_filter

    # get the model manager method depending on the cluster filter
    # and call it to get the base queryset
    clusters = get_objects_for_user(
        request.user,
        'clusters.view_cluster',
        getattr(Cluster.objects, clusters_shown)().order_by('-start_date'),
        use_groups=False,
        with_superuser=False,
    )

    sparkjob_qs = SparkJob.objects.all().order_by('-start_date')
    group = Group.objects.filter(name='Spark job maintainers').first()
    is_sparkjob_maintainer = group and group in request.user.groups.all()

    # Filters for jobs.
    default_job_filter = 'mine'
    jobs_filters = ['mine', 'all']

    jobs_shown = request.GET.get('jobs', default_job_filter)
    if jobs_shown not in jobs_filters:
        jobs_shown = default_job_filter

    # Redirect if user isn't in the right group.
    if jobs_shown == 'all' and not is_sparkjob_maintainer:
        return redirect('dashboard')

    if jobs_shown == 'mine':
        spark_jobs = get_objects_for_user(
            request.user,
            'jobs.view_sparkjob',
            sparkjob_qs,
            use_groups=False,
            with_superuser=False,
        )
    elif jobs_shown == 'all':
        spark_jobs = get_objects_for_group(
            group,
            'jobs.view_sparkjob',
            sparkjob_qs,
            any_perm=False,
            accept_global_perms=False,
        )

    # a list of modification datetimes of the clusters and Spark jobs to use
    # for getting the last changes on the dashboard
    cluster_mod_datetimes = list(clusters.values_list('modified_at', flat=True))
    spark_job_mod_datetimes = [
        spark_job.latest_run.modified_at
        for spark_job in spark_jobs.with_runs().order_by('-runs__modified_at')
    ]
    modified_datetimes = sorted(cluster_mod_datetimes + spark_job_mod_datetimes, reverse=True)

    context = {
        'clusters': clusters,
        'clusters_shown': clusters_shown,
        'clusters_filters': clusters_filters,
        'spark_jobs': spark_jobs,
        'jobs_shown': jobs_shown,
        'jobs_filters': jobs_filters,
        'is_sparkjob_maintainer': is_sparkjob_maintainer,
    }
    if modified_datetimes:
        context['modified_date'] = modified_datetimes[0]

    return TemplateResponse(request, 'atmo/dashboard.html', context=context)


@requires_csrf_token
def server_error(request, template_name='500.html'):
    """
    500 error handler.

    Templates: :template:`500.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return HttpResponseServerError('<h1>Server Error (500)</h1>', content_type='text/html')
    return HttpResponseServerError(template.render(Context({
        'request': request,
    })))
