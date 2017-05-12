# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import http
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist, loader
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME, ERROR_403_TEMPLATE_NAME
from django.views.generic.base import TemplateView
from guardian.shortcuts import get_objects_for_group, get_objects_for_user

from .clusters.models import Cluster
from .decorators import modified_date
from .jobs.models import SparkJob


@method_decorator(login_required, name='dispatch')
@method_decorator(modified_date, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'atmo/dashboard.html'
    http_method_names = ['get', 'head']
    # allowed filters for clusters
    active_cluster_filter = 'active'
    default_cluster_filter = active_cluster_filter
    clusters_filters = [active_cluster_filter, 'terminated', 'failed', 'all']
    # Filters for jobs.
    all_job_filter = 'all'
    mine_job_filter = 'mine'
    default_job_filter = mine_job_filter
    jobs_filters = [mine_job_filter, all_job_filter]
    maintainer_group_name = 'Spark job maintainers'

    def dispatch(self, request, *args, **kwargs):
        self.clusters_shown = self.request.GET.get('clusters', self.default_cluster_filter)
        if self.clusters_shown not in self.clusters_filters:
            self.clusters_shown = self.default_cluster_filter

        self.jobs_maintainer_group = Group.objects.filter(name=self.maintainer_group_name).first()
        self.is_sparkjob_maintainer = (
            self.jobs_maintainer_group and
            self.jobs_maintainer_group in self.request.user.groups.all()
        )

        self.jobs_shown = self.request.GET.get('jobs', self.default_job_filter)
        if self.jobs_shown not in self.jobs_filters:
            self.jobs_shown = self.default_job_filter

        # Redirect if user isn't in the right group.
        if self.jobs_shown == self.all_job_filter and not self.is_sparkjob_maintainer:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # get the model manager method depending on the cluster filter
        # and call it to get the base queryset
        clusters = get_objects_for_user(
            self.request.user,
            'clusters.view_cluster',
            getattr(Cluster.objects, self.clusters_shown)().order_by('-start_date'),
            use_groups=False,
            with_superuser=False,
        )

        sparkjob_qs = SparkJob.objects.all().order_by('-start_date')

        if self.jobs_shown == self.mine_job_filter:
            spark_jobs = get_objects_for_user(
                self.request.user,
                'jobs.view_sparkjob',
                sparkjob_qs,
                use_groups=False,
                with_superuser=False,
            )
        elif self.jobs_shown == self.all_job_filter:
            spark_jobs = get_objects_for_group(
                self.jobs_maintainer_group,
                'jobs.view_sparkjob',
                sparkjob_qs,
                any_perm=False,
                accept_global_perms=False,
            )
        else:
            spark_jobs = sparkjob_qs.none()

        context.update({
            'clusters': clusters,
            'spark_jobs': spark_jobs,
        })

        # a list of modification datetimes of the clusters and Spark jobs to use
        # for getting the last changes on the dashboard
        cluster_mod_datetimes = list(clusters.values_list('modified_at', flat=True))
        spark_job_mod_datetimes = [
            spark_job.latest_run.modified_at
            for spark_job in spark_jobs.with_runs().order_by('-runs__modified_at')
        ]
        modified_datetimes = sorted(cluster_mod_datetimes + spark_job_mod_datetimes, reverse=True)

        if modified_datetimes:
            context['modified_date'] = modified_datetimes[0]

        return context


@requires_csrf_token
def server_error(request, template_name=ERROR_500_TEMPLATE_NAME):
    """
    500 error handler.

    Templates: :template:`500.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_500_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return http.HttpResponseServerError('<h1>Server Error (500)</h1>', content_type='text/html')
    return http.HttpResponseServerError(template.render(request=request))


# This can be called when CsrfViewMiddleware.process_view has not run,
# therefore need @requires_csrf_token in case the template needs
# {% csrf_token %}.
@requires_csrf_token
def permission_denied(request, exception, template_name=ERROR_403_TEMPLATE_NAME):
    """
    Permission denied (403) handler.

    Templates: :template:`403.html`
    Context: None

    If the template does not exist, an Http403 response containing the text
    "403 Forbidden" (as per RFC 7231) will be returned.
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_403_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return http.HttpResponseForbidden('<h1>403 Forbidden</h1>', content_type='text/html')
    return http.HttpResponseForbidden(
        template.render(request=request, context={'exception': force_text(exception)})
    )
