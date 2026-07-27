import datetime as dt
from http import HTTPStatus
from itertools import groupby
from pathlib import Path

import segno
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils._os import safe_join
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST

from djangolondon.forms import EntryEmailForm, EntryForm
from djangolondon.models import Meetup, Prize, PrizeDraw, Speaker, Talk


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


def _entry_session_key(draw: PrizeDraw) -> str:
    return f"prize_draw_entry_{draw.pk}"


def _get_entry(request: HttpRequest, draw: PrizeDraw):
    entry_id = request.session.get(_entry_session_key(draw))
    if entry_id is None:
        return None
    return draw.entries.filter(pk=entry_id).first()


def _entry_context(
    request: HttpRequest,
    draw: PrizeDraw,
    *,
    entry_form: EntryForm | None = None,
    email_form: EntryEmailForm | None = None,
) -> dict:
    entry = _get_entry(request, draw)
    won_prize = entry.won_prize() if entry is not None else None
    prizes_remaining = draw.next_prize() is not None
    return {
        "draw": draw,
        "entry": entry,
        "won_prize": won_prize,
        "prizes_remaining": prizes_remaining,
        # Attendees only need live updates while they are waiting to hear.
        "polling": entry is not None and won_prize is None and prizes_remaining,
        "entry_form": entry_form if entry_form is not None else EntryForm(),
        "email_form": email_form if email_form is not None else EntryEmailForm(),
    }


def _entry_response(
    request: HttpRequest, context: dict, *, status: int = HTTPStatus.OK
) -> HttpResponse:
    return render(request, "prize_draws/entry.html", context, status=status)


@require_GET
def prize_draw_join(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    return render(
        request,
        "prize_draws/join.html",
        {"title": draw.name, **_entry_context(request, draw)},
    )


@require_GET
def prize_draw_status(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    return _entry_response(request, _entry_context(request, draw))


@require_POST
def prize_draw_enter(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    if not request.htmx:
        return redirect(f"/prize-draws/{draw.slug}/")

    if _get_entry(request, draw) is not None or not draw.entries_open:
        return _entry_response(request, _entry_context(request, draw))

    form = EntryForm(request.POST)
    if not form.is_valid():
        context = _entry_context(request, draw, entry_form=form)
        return _entry_response(request, context, status=HTTPStatus.UNPROCESSABLE_ENTITY)

    entry = form.save(commit=False)
    entry.draw = draw
    entry.save()
    request.session[_entry_session_key(draw)] = entry.pk
    return _entry_response(request, _entry_context(request, draw))


@require_POST
def prize_draw_email(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    if not request.htmx:
        return redirect(f"/prize-draws/{draw.slug}/")

    entry = _get_entry(request, draw)
    if entry is None or entry.won_prize() is None:
        return _entry_response(request, _entry_context(request, draw))

    form = EntryEmailForm(request.POST, instance=entry)
    if not form.is_valid():
        context = _entry_context(request, draw, email_form=form)
        return _entry_response(request, context, status=HTTPStatus.UNPROCESSABLE_ENTITY)

    form.save()
    return _entry_response(request, _entry_context(request, draw))


def _screen_context(draw: PrizeDraw) -> dict:
    next_prize = draw.next_prize()
    return {
        "draw": draw,
        "next_prize": next_prize,
        "entry_count": draw.entries.count(),
        "can_draw": next_prize is not None and draw.eligible_entries().exists(),
        "won_prizes": (
            draw.prizes.filter(winner__isnull=False)
            .select_related("winner")
            .order_by("-drawn_at")
        ),
    }


def _screen_response(request: HttpRequest, draw: PrizeDraw) -> HttpResponse:
    return render(request, "prize_draws/screen_status.html", _screen_context(draw))


@staff_member_required
@require_GET
def prize_draw_screen(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    join_url = request.build_absolute_uri(f"/prize-draws/{draw.slug}/")
    qr_svg = segno.make(join_url, error="m").svg_inline(
        scale=8,
        dark="#092e20",
        light="#ffffff",
    )
    return render(
        request,
        "prize_draws/screen.html",
        {
            "title": draw.name,
            "join_url": join_url,
            # Safe: the SVG comes from segno, not from user input.
            "qr_svg": mark_safe(qr_svg),
            **_screen_context(draw),
        },
    )


@staff_member_required
@require_GET
def prize_draw_screen_status(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    return _screen_response(request, draw)


@staff_member_required
@require_POST
def prize_draw_draw(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    draw.draw_prize()
    if not request.htmx:
        return redirect(f"/prize-draws/{draw.slug}/screen/")
    return _screen_response(request, draw)


@require_GET
def prize_voucher(request: HttpRequest, pk: int) -> HttpResponse:
    prize = get_object_or_404(Prize.objects.select_related("draw"), pk=pk)
    entry = _get_entry(request, prize.draw)
    if not prize.voucher or entry is None or prize.winner_id != entry.pk:
        raise Http404
    return FileResponse(
        prize.voucher.open("rb"),
        as_attachment=True,
        filename=Path(prize.voucher.name).name,
    )


@staff_member_required
@require_GET
def media_file(request: HttpRequest, path: str) -> HttpResponse:
    file_path = Path(safe_join(settings.MEDIA_ROOT, path))
    if not file_path.is_file():
        raise Http404
    return FileResponse(file_path.open("rb"))


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
