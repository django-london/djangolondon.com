import datetime as dt
from itertools import groupby

from django.conf import settings
from django.db.models import Prefetch
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from djangolondon.models import Meetup, Speaker, Talk


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
    meetup_count = sum(len(ms) for _, ms in grouped)
    return render(
        request,
        "meetups/list.html",
        {
            "title": "Meetups",
            "meetup_count": meetup_count,
            "grouped_meetups": grouped,
        },
    )


def meetup_detail(request, date: dt.date):
    meetup = get_object_or_404(
        Meetup.objects.prefetch_related("talk_set__speakers"),
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


def speaker_list(request):
    speakers = Speaker.objects.order_by("name")
    return render(
        request,
        "speakers/list.html",
        {
            "title": "Speakers",
            "speakers": speakers,
        },
    )


def speaker_detail(request, slug: str):
    speaker = get_object_or_404(
        Speaker.objects.prefetch_related(
            Prefetch(
                "talk_set",
                queryset=Talk.objects.select_related("meetup").order_by(
                    "-meetup__date"
                ),
            )
        ),
        slug=slug,
    )
    return render(
        request,
        "speakers/detail.html",
        {
            "title": speaker.name,
            "speaker": speaker,
        },
    )


@require_GET
def meetup_slides(request: HttpRequest, date: str, filename: str) -> HttpResponse:
    path = settings.BASE_DIR / "data/slides" / date / filename
    if not path.is_file():
        raise Http404
    return FileResponse(path.open("rb"))


@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.BASE_DIR / "djangolondon/static/favicon.svg").open("rb")
    return FileResponse(file)


@require_GET
def atproto_did(request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        "did:plc:r4l26ukwabszkecqnsv77jt3",
        content_type="text/plain",
    )
