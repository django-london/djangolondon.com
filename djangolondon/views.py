import datetime as dt
from itertools import groupby

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from djangolondon.models import Meetup


def index(request):
    meetups = Meetup.objects.all()[:3]
    return render(request, "index.html", {"meetups": meetups})


def code_of_conduct(request):
    return render(
        request,
        "code-of-conduct.html",
        {"title": "Code of Conduct"},
    )


def meetup_list(request):
    all_meetups = Meetup.objects.all()
    grouped = [
        (year, list(ms)) for year, ms in groupby(all_meetups, key=lambda m: m.date.year)
    ]
    return render(
        request,
        "meetups/list.html",
        {
            "title": "Meetups",
            "grouped_meetups": grouped,
        },
    )


def meetup_detail(request, date: dt.date):
    meetup = get_object_or_404(
        Meetup.objects.prefetch_related("talk_set__speaker"),
        date__date=date,
    )
    return render(
        request,
        "meetups/detail.html",
        {
            "title": meetup.title,
            "meetup": meetup,
        },
    )


def meetup_redirect(request, date: dt.date):
    return redirect(f"/meetups/{date.isoformat()}/", permanent=True)


@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.BASE_DIR / "djangolondon/static/favicon.svg").open("rb")
    return FileResponse(file)
