from django.shortcuts import render

from session_csrf import anonymous_csrf


@anonymous_csrf
def home(request):
    return render(request, 'analysis_service/index.jinja')
