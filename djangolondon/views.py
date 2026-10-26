import datetime as dt
from http import HTTPStatus
from io import BytesIO
from itertools import groupby
from zoneinfo import ZoneInfo

import segno
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import TemplateDoesNotExist
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from djangolondon import live_quiz
from djangolondon.forms import EntryForm, PlayerForm
from djangolondon.live_quiz import LiveQuiz
from djangolondon.models import (
    Answer,
    Meetup,
    Player,
    Prize,
    PrizeDraw,
    Quiz,
    Speaker,
    Talk,
)

london_tz = ZoneInfo("Europe/London")


def index(request):
    today = timezone.now().astimezone(london_tz).date()
    start_of_today = dt.datetime.combine(today, dt.time.min, tzinfo=london_tz)
    start_of_tomorrow = dt.datetime.combine(
        today + dt.timedelta(days=1), dt.time.min, tzinfo=london_tz
    )
    start_of_next_month = dt.datetime.combine(
        (today.replace(day=1) + dt.timedelta(days=32)).replace(day=1),
        dt.time.min,
        tzinfo=london_tz,
    )
    meetups = list(Meetup.objects.only("date"))
    past = [m for m in meetups if m.date < start_of_today]
    today_meetups = [m for m in meetups if start_of_today <= m.date < start_of_tomorrow]
    month = [m for m in meetups if start_of_tomorrow <= m.date < start_of_next_month]
    future = [m for m in meetups if m.date >= start_of_next_month]
    return render(
        request,
        "index.html",
        {
            "today_meetups": today_meetups,
            "month_meetups": month[::-1],
            "future_meetups": future[::-1],
            "past_meetups": past[:3],
        },
    )


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
) -> dict:
    entry = _get_entry(request, draw)
    # One query for the prizes: a draw only ever has a handful, and this page
    # is polled by every phone in the room.
    prizes = list(draw.prizes.defer("voucher"))
    next_prize = next((p for p in prizes if p.winner_id is None), None)
    won_prize = None
    if entry is not None:
        won_prize = next((p for p in prizes if p.winner_id == entry.pk), None)
    return {
        "draw": draw,
        "entry": entry,
        "won_prize": won_prize,
        "prizes_remaining": next_prize is not None,
        # Attendees only need live updates while they are waiting to hear.
        "polling": entry is not None and won_prize is None and next_prize is not None,
        "entry_form": entry_form if entry_form is not None else EntryForm(),
    }


def _entry_response(
    request: HttpRequest, context: dict, *, status: int = HTTPStatus.OK
) -> HttpResponse:
    return render(request, "prize_draws/entry.html", context, status=status)


@transaction.non_atomic_requests
@require_GET
def prize_draw_join(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    return render(
        request,
        "prize_draws/join.html",
        {"title": draw.name, **_entry_context(request, draw)},
    )


@transaction.non_atomic_requests
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


def _screen_context(draw: PrizeDraw) -> dict:
    # One query for the prizes and one for the entries. Everything the screen
    # shows is derived from those two lists rather than queried separately.
    prizes = list(draw.prizes.defer("voucher"))
    entries = list(draw.entries.all())
    entries_by_id = {entry.pk: entry for entry in entries}

    next_prize = next((p for p in prizes if p.winner_id is None), None)
    winner_ids = {p.winner_id for p in prizes}
    won = sorted(
        (p for p in prizes if p.winner_id in entries_by_id),
        key=lambda prize: prize.drawn_at,
        reverse=True,
    )
    return {
        "draw": draw,
        "next_prize": next_prize,
        "entries": entries,
        "entry_count": len(entries),
        "can_draw": next_prize is not None
        and any(entry.pk not in winner_ids for entry in entries),
        "won_prizes": [(prize, entries_by_id[prize.winner_id]) for prize in won],
    }


def _qr_svg(url: str) -> str:
    svg = segno.make(url, error="m").svg_inline(
        scale=8,
        dark="#092e20",
        light="#ffffff",
        # A viewBox instead of a fixed size, so CSS can scale it to the screen.
        omitsize=True,
    )
    # Safe: the SVG comes from segno, not from user input.
    return mark_safe(svg)


def _screen_response(request: HttpRequest, draw: PrizeDraw) -> HttpResponse:
    return render(request, "prize_draws/screen_status.html", _screen_context(draw))


@staff_member_required
@require_GET
def prize_draw_screen(request: HttpRequest, slug: str) -> HttpResponse:
    draw = get_object_or_404(PrizeDraw, slug=slug)
    join_url = request.build_absolute_uri(f"/prize-draws/{draw.slug}/")
    return render(
        request,
        "prize_draws/screen.html",
        {
            "title": draw.name,
            "join_url": join_url,
            "qr_svg": _qr_svg(join_url),
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


@staff_member_required
@require_POST
def prize_draw_remove_entry(request: HttpRequest, slug: str, pk: int) -> HttpResponse:
    """Drop an entry from the draw, for when a name should not be on screen."""
    draw = get_object_or_404(PrizeDraw, slug=slug)
    entry = draw.entries.filter(pk=pk).first()
    if entry is not None:
        # Anything this entry won goes back in the pot.
        draw.prizes.filter(winner=entry).update(drawn_at=None)
        entry.delete()
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
        BytesIO(bytes(prize.voucher)),
        as_attachment=True,
        filename=prize.voucher_filename,
        content_type="application/pdf",
    )


def quiz_list(request: HttpRequest) -> HttpResponse:
    quizzes = Quiz.objects.filter(published=True).annotate(
        question_count=Count("questions")
    )
    return render(
        request,
        "quizzes/list.html",
        {"title": "Quizzes", "quizzes": quizzes},
    )


@require_http_methods(["GET", "POST"])
def quiz_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Play a quiz alone: answer every question, then see how you did."""
    # Organizers can try out a quiz before it is published.
    quizzes = (
        Quiz.objects.all()
        if request.user.is_staff
        else Quiz.objects.filter(published=True)
    )
    quiz = get_object_or_404(quizzes, slug=slug)
    questions = list(quiz.questions.all())
    context = {"title": quiz.title, "quiz": quiz, "questions": questions}

    if request.method == "POST":
        results = []
        for question in questions:
            chosen = request.POST.get(f"question-{question.pk}")
            if chosen not in dict(question.choices()):
                chosen = None
            results.append(
                {
                    "question": question,
                    "chosen": chosen,
                    "correct": chosen == question.answer,
                }
            )
        context["results"] = results
        context["score"] = sum(1 for result in results if result["correct"])
        if request.htmx:
            return render(request, "quizzes/self_play.html", context)

    return render(request, "quizzes/detail.html", context)


def _player_session_key(quiz: Quiz) -> str:
    return f"quiz_player_{quiz.pk}"


def _get_player(request: HttpRequest, quiz: Quiz) -> Player | None:
    player_id = request.session.get(_player_session_key(quiz))
    if player_id is None:
        return None
    return quiz.players.filter(pk=player_id).first()


def _player_context(
    request: HttpRequest,
    quiz: Quiz,
    *,
    player_form: PlayerForm | None = None,
) -> dict:
    player = _get_player(request, quiz)
    live = LiveQuiz.load_for_player(quiz, player)
    context = {
        "quiz": quiz,
        "live": live,
        "player": player,
        # Players only need live updates once they have joined, and until
        # there is nothing left for their phone to show.
        "polling": player is not None and live.phase != live_quiz.RESULTS,
        "player_form": player_form if player_form is not None else PlayerForm(),
    }
    if player is not None:
        context["choice"] = live.choice(player)
        context["score"] = live.score(player, through=live.number)
    return context


def _player_response(
    request: HttpRequest, context: dict, *, status: int = HTTPStatus.OK
) -> HttpResponse:
    return render(request, "quizzes/player.html", context, status=status)


@transaction.non_atomic_requests
@require_GET
def quiz_live(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    return render(
        request,
        "quizzes/live.html",
        {"title": quiz.title, **_player_context(request, quiz)},
    )


@transaction.non_atomic_requests
@require_GET
def quiz_live_status(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    return _player_response(request, _player_context(request, quiz))


@require_POST
def quiz_live_join(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    if not request.htmx:
        return redirect(f"/quizzes/{quiz.slug}/live/")

    live = LiveQuiz.load_for_player(quiz, None)
    if _get_player(request, quiz) is not None or not live.can_join:
        return _player_response(request, _player_context(request, quiz))

    form = PlayerForm(request.POST)
    if not form.is_valid():
        context = _player_context(request, quiz, player_form=form)
        return _player_response(
            request, context, status=HTTPStatus.UNPROCESSABLE_ENTITY
        )

    player = form.save(commit=False)
    player.quiz = quiz
    player.save()
    request.session[_player_session_key(quiz)] = player.pk
    return _player_response(request, _player_context(request, quiz))


@require_POST
def quiz_live_answer(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    if not request.htmx:
        return redirect(f"/quizzes/{quiz.slug}/live/")

    player = _get_player(request, quiz)
    live = LiveQuiz.load_for_player(quiz, player)
    question = live.question
    # The question is checked against the one on the player’s phone, so that a
    # tap that lands just after the quizmaster moves on does not count as an
    # answer to the next question.
    if (
        player is not None
        and live.phase == live_quiz.QUESTION
        and request.POST.get("question") == str(question.pk)
        and (choice := request.POST.get("choice")) in dict(question.choices())
    ):
        Answer.objects.update_or_create(
            player=player, question=question, defaults={"choice": choice}
        )
    return _player_response(request, _player_context(request, quiz))


def _quiz_screen_response(request: HttpRequest, quiz: Quiz) -> HttpResponse:
    return render(
        request,
        "quizzes/screen_status.html",
        {"quiz": quiz, "live": LiveQuiz.load(quiz), **_join_context(request, quiz)},
    )


def _join_context(request: HttpRequest, quiz: Quiz) -> dict:
    join_url = request.build_absolute_uri(f"/quizzes/{quiz.slug}/live/")
    return {"join_url": join_url, "qr_svg": _qr_svg(join_url)}


def _posted_step(request: HttpRequest) -> int | None:
    """The step the quizmaster’s screen was on when they pressed a button."""
    try:
        return int(request.POST.get("step", ""))
    except ValueError:
        return None


@staff_member_required
@require_GET
def quiz_screen(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    return render(
        request,
        "quizzes/screen.html",
        {
            "title": quiz.title,
            "quiz": quiz,
            "live": LiveQuiz.load(quiz),
            **_join_context(request, quiz),
        },
    )


@staff_member_required
@require_GET
def quiz_screen_status(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    return _quiz_screen_response(request, quiz)


@staff_member_required
@require_POST
def quiz_screen_next(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    step = _posted_step(request)
    if step is not None and step < LiveQuiz.load(quiz).last_step:
        quiz.advance(step, step + 1)
    if not request.htmx:
        return redirect(f"/quizzes/{quiz.slug}/screen/")
    return _quiz_screen_response(request, quiz)


@staff_member_required
@require_POST
def quiz_screen_back(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    step = _posted_step(request)
    if step is not None and step > 0:
        quiz.advance(step, step - 1)
    if not request.htmx:
        return redirect(f"/quizzes/{quiz.slug}/screen/")
    return _quiz_screen_response(request, quiz)


@staff_member_required
@require_POST
def quiz_screen_reset(request: HttpRequest, slug: str) -> HttpResponse:
    quiz = get_object_or_404(Quiz, slug=slug)
    quiz.reset()
    if not request.htmx:
        return redirect(f"/quizzes/{quiz.slug}/screen/")
    return _quiz_screen_response(request, quiz)


@staff_member_required
@require_POST
def quiz_screen_remove_player(request: HttpRequest, slug: str, pk: int) -> HttpResponse:
    """Drop a player from the quiz, for when a name should not be on screen."""
    quiz = get_object_or_404(Quiz, slug=slug)
    quiz.players.filter(pk=pk).delete()
    if not request.htmx:
        return redirect(f"/quizzes/{quiz.slug}/screen/")
    return _quiz_screen_response(request, quiz)


@require_GET
def meetup_slides(request: HttpRequest, date: str, filename: str) -> HttpResponse:
    path = settings.BASE_DIR / "data/slides" / date / filename
    if not path.is_file():
        raise Http404
    return FileResponse(path.open("rb"))


@require_GET
def organizer_index(request: HttpRequest) -> HttpResponse:
    decks_dir = settings.BASE_DIR / "djangolondon/templates/slides/decks"
    dates = sorted(
        (dt.date.fromisoformat(path.stem) for path in decks_dir.glob("*.html")),
        reverse=True,
    )
    grouped = [(year, list(ds)) for year, ds in groupby(dates, key=lambda d: d.year)]
    return render(
        request,
        "slides/index.html",
        {"title": "Organizers’ slides", "grouped_decks": grouped},
    )


@require_GET
def organizer_slides(request: HttpRequest, date: dt.date) -> HttpResponse:
    try:
        return render(request, f"slides/decks/{date.isoformat()}.html")
    except TemplateDoesNotExist:
        raise Http404


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
