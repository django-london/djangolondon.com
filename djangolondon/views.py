import datetime as dt

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from djangolondon.models import Meetup


def index(request):
    meetups = Meetup.objects.all()
    return render(request, "index.html", {"meetups": meetups})


def code_of_conduct(request):
    return render(
        request,
        "code-of-conduct.html",
        {"title": "Code of Conduct"},
    )


def meetup(request, date: dt.date):
    meetup = get_object_or_404(
        Meetup.objects.prefetch_related("talk_set__speaker"),
        date__date=date,
    )
    return render(request, "meetup.html", {"meetup": meetup})


@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.BASE_DIR / "djangolondon/static/favicon.svg").open("rb")
    return FileResponse(file)
