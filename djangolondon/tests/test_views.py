import datetime as dt
from http import HTTPStatus

import time_machine
from django.contrib.auth.models import User
from django.test import TestCase

from djangolondon.models import (
    Answer,
    Entry,
    Meetup,
    Player,
    Prize,
    PrizeDraw,
    Question,
    Quiz,
    Speaker,
)


class IndexTests(TestCase):
    def test_success(self):
        response = self.client.get("/")
        assert response.status_code == HTTPStatus.OK
        assert len(response.context["past_meetups"]) <= 3
        assert "/meetups/" in response.text

    @time_machine.travel(dt.datetime(2040, 6, 10, 23, 30, tzinfo=dt.UTC), tick=False)
    def test_today_month_and_future_meetups(self):
        bst = dt.timezone(dt.timedelta(hours=1))
        past = Meetup.objects.create(
            title="Past", date=dt.datetime(2040, 6, 9, 18, 15, tzinfo=bst)
        )
        today = Meetup.objects.create(
            title="Today", date=dt.datetime(2040, 6, 11, 18, 15, tzinfo=bst)
        )
        soon = Meetup.objects.create(
            title="Soon", date=dt.datetime(2040, 6, 12, 18, 15, tzinfo=bst)
        )
        month_end = Meetup.objects.create(
            title="Month end", date=dt.datetime(2040, 6, 30, 18, 15, tzinfo=bst)
        )
        later = Meetup.objects.create(
            title="Later", date=dt.datetime(2040, 7, 9, 18, 15, tzinfo=bst)
        )

        response = self.client.get("/")

        assert response.status_code == HTTPStatus.OK
        assert list(response.context["today_meetups"]) == [today]
        assert list(response.context["month_meetups"]) == [soon, month_end]
        assert list(response.context["future_meetups"]) == [later]
        assert list(response.context["past_meetups"])[0] == past
        assert "<h2>Today's Meetup</h2>" in response.text
        assert "<h2>This Month's Meetup</h2>" in response.text
        assert "<h2>Future Meetups</h2>" in response.text
        assert "<h2>Past Meetups</h2>" in response.text

    @time_machine.travel(dt.datetime(2100, 1, 1, 12, 0, tzinfo=dt.UTC), tick=False)
    def test_no_today_month_or_future_meetups(self):
        response = self.client.get("/")

        assert response.status_code == HTTPStatus.OK
        assert "Today's Meetup" not in response.text
        assert "This Month's Meetup" not in response.text
        assert "Future Meetups" not in response.text
        assert "<h2>Past Meetups</h2>" in response.text


class CodeOfConductTests(TestCase):
    def test_success(self):
        response = self.client.get("/code-of-conduct/")
        assert response.status_code == HTTPStatus.OK
        assert "<title>Code of Conduct | Django London</title>" in response.text
        assert "Be Awesome to Each Other" in response.text


class MeetupListTests(TestCase):
    def test_success(self):
        response = self.client.get("/meetups/")
        assert response.status_code == HTTPStatus.OK
        grouped = response.context["grouped_meetups"]
        years = [year for year, _ in grouped]
        assert years == sorted(years, reverse=True)
        assert len(years) == len(set(years))
        assert "Django London has held" in response.text
        assert "/meetups/2021-05-18/" in response.text


class MeetupDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.speaker = Speaker.objects.get(slug="paolo-melchiorre")

    def test_success(self):
        response = self.client.get("/meetups/2021-05-18/")
        assert response.status_code == HTTPStatus.OK
        assert "May Django Meetup" in response.text
        assert "Maps with Django" in response.text
        assert f"/speakers/{self.speaker.slug}/" in response.text
        assert "Paolo Melchiorre" in response.text

    def test_not_found(self):
        response = self.client.get("/meetups/2000-01-01/")
        assert response.status_code == HTTPStatus.NOT_FOUND


class MeetupRedirectTests(TestCase):
    def test_redirect(self):
        response = self.client.get("/meetup/2021-05-18/")
        assert response.status_code == HTTPStatus.MOVED_PERMANENTLY
        assert response["Location"] == "/meetups/2021-05-18/"


class SpeakerListTests(TestCase):
    def test_success(self):
        response = self.client.get("/speakers/")
        assert response.status_code == HTTPStatus.OK
        assert "<title>Speakers | Django London</title>" in response.text
        assert "Django London has hosted" in response.text
        assert "/speakers/paolo-melchiorre/" in response.text


class SpeakerDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.speaker = Speaker.objects.get(slug="paolo-melchiorre")

    def test_success(self):
        response = self.client.get(f"/speakers/{self.speaker.slug}/")
        assert response.status_code == HTTPStatus.OK
        assert "<title>Paolo Melchiorre | Django London</title>" in response.text
        assert "Maps with Django" in response.text
        assert "/meetups/2021-05-18/" in response.text

    def test_not_found(self):
        response = self.client.get("/speakers/does-not-exist/")
        assert response.status_code == HTTPStatus.NOT_FOUND


class MeetupSlidesTests(TestCase):
    def test_success(self):
        response = self.client.get("/slides/2018-10-09/django-sql.pdf")
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "application/pdf"

    def test_not_found(self):
        response = self.client.get("/slides/2018-10-09/does-not-exist.pdf")
        assert response.status_code == HTTPStatus.NOT_FOUND


class OrganizerIndexTests(TestCase):
    def test_success(self):
        response = self.client.get("/organizers/")
        assert response.status_code == HTTPStatus.OK
        assert "/organizers/2026-10-14/" in response.text
        assert "14 October" in response.text


class OrganizerSlidesTests(TestCase):
    def test_success(self):
        response = self.client.get("/organizers/2026-10-14/")
        assert response.status_code == HTTPStatus.OK
        assert "Who lost our customers?" in response.text
        assert "/static/slides/reveal.js" in response.text
        assert "<div class=slides>\n\n<section>" in response.text
        nonce = response.context["csp_nonce"]
        assert f"nonce={nonce}" in response.text

    def test_not_found(self):
        response = self.client.get("/organizers/2000-01-01/")
        assert response.status_code == HTTPStatus.NOT_FOUND


class FaviconTests(TestCase):
    def test_success(self):
        response = self.client.get("/favicon.ico")
        assert response.status_code == HTTPStatus.OK


class AtprotoDidTests(TestCase):
    def test_success(self):
        response = self.client.get("/.well-known/atproto-did")
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/plain"
        assert response.text == "did:plc:r4l26ukwabszkecqnsv77jt3"


HTMX_HEADERS = {"HX-Request": "true"}


class PrizeDrawTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")
        cls.prize = Prize.objects.create(draw=cls.draw, name="Django Book")

    def enter(self, name="Alice"):
        """Enter the draw as an attendee, returning their entry."""
        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": name},
            headers=HTMX_HEADERS,
        )
        assert response.status_code == HTTPStatus.OK
        return Entry.objects.get(name=name)

    def login_organizer(self):
        User.objects.create_user("organizer", password="thames", is_staff=True)
        self.client.login(username="organizer", password="thames")


class PrizeDrawJoinTests(PrizeDrawTestCase):
    def test_success(self):
        response = self.client.get("/prize-draws/june-2026/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>June 2026 Draw | Django London</title>" in response.text
        assert "Enter the draw" in response.text
        assert "/static/django_htmx/htmx-4.min.js" in response.text

    def test_not_found(self):
        response = self.client.get("/prize-draws/does-not-exist/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_entries_closed(self):
        PrizeDraw.objects.filter(pk=self.draw.pk).update(entries_open=False)

        response = self.client.get("/prize-draws/june-2026/")

        assert response.status_code == HTTPStatus.OK
        assert "Entries are closed" in response.text

    def test_already_entered(self):
        self.enter()

        response = self.client.get("/prize-draws/june-2026/")

        assert response.status_code == HTTPStatus.OK
        assert "You’re in the draw, Alice." in response.text
        assert "hx-get=/prize-draws/june-2026/status/" in response.text


class PrizeDrawEnterTests(PrizeDrawTestCase):
    def test_success(self):
        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": "Alice"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        assert "You’re in the draw, Alice." in response.text
        entry = Entry.objects.get()
        assert entry.draw == self.draw
        assert entry.name == "Alice"
        assert self.client.session[f"prize_draw_entry_{self.draw.pk}"] == entry.pk

    def test_invalid(self):
        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": ""},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert "This field is required." in response.text
        assert not Entry.objects.exists()

    def test_without_htmx_redirects(self):
        response = self.client.post("/prize-draws/june-2026/enter/", {"name": "Alice"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/prize-draws/june-2026/"
        assert not Entry.objects.exists()

    def test_twice_does_not_create_a_second_entry(self):
        self.enter()

        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": "Alice Again"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        assert Entry.objects.count() == 1

    def test_entries_closed(self):
        PrizeDraw.objects.filter(pk=self.draw.pk).update(entries_open=False)

        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": "Alice"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        assert "Entries are closed" in response.text
        assert not Entry.objects.exists()

    def test_get_not_allowed(self):
        response = self.client.get("/prize-draws/june-2026/enter/")

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


class PrizeDrawStatusTests(PrizeDrawTestCase):
    def test_waiting(self):
        self.enter()

        response = self.client.get(
            "/prize-draws/june-2026/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "You’re in the draw, Alice." in response.text

    def test_won(self):
        entry = self.enter()
        self.draw.draw_prize()

        response = self.client.get(
            "/prize-draws/june-2026/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "You won!" in response.text
        assert "Django Book" in response.text
        assert "Come and see an organizer to collect it." in response.text
        # Winners have no more news to wait for.
        assert "hx-get=" not in response.text
        assert self.prize.pk == entry.prize.pk

    def test_lost(self):
        self.enter()
        Entry.objects.create(draw=self.draw, name="Bob")
        self.prize.winner = Entry.objects.get(name="Bob")
        self.prize.save()

        response = self.client.get(
            "/prize-draws/june-2026/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "you didn’t win this time" in response.text
        assert "hx-get=" not in response.text

    def test_not_found(self):
        response = self.client.get("/prize-draws/does-not-exist/status/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class PrizeDrawScreenTests(PrizeDrawTestCase):
    def test_requires_staff(self):
        response = self.client.get("/prize-draws/june-2026/screen/")

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"].startswith("/organizers-admin/login/")

    def test_success(self):
        self.login_organizer()

        response = self.client.get("/prize-draws/june-2026/screen/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>June 2026 Draw | Django London</title>" in response.text
        assert "<svg" in response.text
        assert "http://testserver/prize-draws/june-2026/" in response.text
        assert "Draw Django Book" in response.text
        assert "0 entries" in response.text
        # Nobody has entered yet, so there is nobody to draw.
        assert "disabled" in response.text

    def test_not_found(self):
        self.login_organizer()

        response = self.client.get("/prize-draws/does-not-exist/screen/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class PrizeDrawScreenStatusTests(PrizeDrawTestCase):
    def test_requires_staff(self):
        response = self.client.get("/prize-draws/june-2026/screen/status/")

        assert response.status_code == HTTPStatus.FOUND

    def test_success(self):
        self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.get(
            "/prize-draws/june-2026/screen/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "1 entry" in response.text
        assert "disabled" not in response.text
        # The room can see who is in.
        assert "In the draw" in response.text
        assert "Alice" in response.text


class PrizeDrawDrawTests(PrizeDrawTestCase):
    def test_requires_staff(self):
        response = self.client.post("/prize-draws/june-2026/screen/draw/")

        assert response.status_code == HTTPStatus.FOUND
        assert not Prize.objects.filter(winner__isnull=False).exists()

    def test_success(self):
        self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.post(
            "/prize-draws/june-2026/screen/draw/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Winners" in response.text
        assert "Alice" in response.text
        assert "All prizes drawn!" in response.text
        self.prize.refresh_from_db()
        assert self.prize.winner == Entry.objects.get()

    def test_without_entries(self):
        self.login_organizer()

        response = self.client.post(
            "/prize-draws/june-2026/screen/draw/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Waiting for entries" in response.text
        self.prize.refresh_from_db()
        assert self.prize.winner is None

    def test_when_everyone_has_won(self):
        self.enter()
        self.client.logout()
        self.login_organizer()
        Prize.objects.create(draw=self.draw, order=2, name="Django Mug")
        self.draw.draw_prize()

        response = self.client.post(
            "/prize-draws/june-2026/screen/draw/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Everyone in the draw has already won a prize." in response.text
        assert not Prize.objects.filter(name="Django Mug", winner__isnull=False)

    def test_without_htmx_redirects(self):
        self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.post("/prize-draws/june-2026/screen/draw/")

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/prize-draws/june-2026/screen/"
        self.prize.refresh_from_db()
        assert self.prize.winner is not None


class PrizeDrawRemoveEntryTests(PrizeDrawTestCase):
    def remove_url(self, entry):
        return f"/prize-draws/june-2026/screen/entries/{entry.pk}/remove/"

    def test_requires_staff(self):
        entry = self.enter()

        response = self.client.post(self.remove_url(entry))

        assert response.status_code == HTTPStatus.FOUND
        assert Entry.objects.filter(pk=entry.pk).exists()

    def test_success(self):
        entry = self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.post(self.remove_url(entry), headers=HTMX_HEADERS)

        assert response.status_code == HTTPStatus.OK
        assert "0 entries" in response.text
        assert not Entry.objects.exists()

    def test_removing_a_winner_returns_the_prize_to_the_pot(self):
        entry = self.enter()
        self.draw.draw_prize()
        self.client.logout()
        self.login_organizer()

        response = self.client.post(self.remove_url(entry), headers=HTMX_HEADERS)

        assert response.status_code == HTTPStatus.OK
        self.prize.refresh_from_db()
        assert self.prize.winner is None
        assert self.prize.drawn_at is None
        assert "Draw Django Book" in response.text

    def test_unknown_entry(self):
        self.login_organizer()

        response = self.client.post(
            "/prize-draws/june-2026/screen/entries/404/remove/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK

    def test_without_htmx_redirects(self):
        entry = self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.post(self.remove_url(entry))

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/prize-draws/june-2026/screen/"
        assert not Entry.objects.exists()


class PrizeDrawPollingTests(PrizeDrawTestCase):
    def test_polls_slowly_while_entries_are_open(self):
        self.enter()

        response = self.client.get("/prize-draws/june-2026/")

        assert 'hx-trigger="every 5s"' in response.text

    def test_polls_quickly_once_the_draw_has_started(self):
        self.enter()
        Prize.objects.create(draw=self.draw, order=2, name="Django Mug")
        # Someone else takes the first prize, so our attendee is still waiting.
        self.prize.winner = Entry.objects.create(draw=self.draw, name="Bob")
        self.prize.save()
        PrizeDraw.objects.filter(pk=self.draw.pk).update(entries_open=False)

        response = self.client.get("/prize-draws/june-2026/")

        assert 'hx-trigger="every 2s"' in response.text


class PrizeVoucherTests(PrizeDrawTestCase):
    def attach_voucher(self):
        self.prize.voucher = b"%PDF-1.7 fake voucher"
        self.prize.voucher_filename = "django-book.pdf"
        self.prize.save()

    def test_success(self):
        self.attach_voucher()
        self.enter()
        self.draw.draw_prize()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.OK
        assert b"".join(response.streaming_content) == b"%PDF-1.7 fake voucher"
        assert "django-book.pdf" in response["Content-Disposition"]

    def test_without_voucher(self):
        self.enter()
        self.draw.draw_prize()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_without_entry(self):
        self.attach_voucher()
        Entry.objects.create(draw=self.draw, name="Bob")
        self.draw.draw_prize()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_for_someone_elses_prize(self):
        self.attach_voucher()
        self.enter()
        self.prize.winner = Entry.objects.create(draw=self.draw, name="Bob")
        self.prize.save()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_not_found(self):
        response = self.client.get("/prizes/404/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class QuizTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quiz = Quiz.objects.create(
            slug="quiz-2026",
            title="Django Quiz 2026",
            date=dt.date(2026, 12, 8),
            description="The quiz from our [December meetup](/meetups/).",
            published=True,
        )
        cls.q1 = Question.objects.create(
            quiz=cls.quiz,
            order=1,
            text="What is `django.db`?",
            choice_a="The ORM",
            choice_b="A guitarist",
            choice_c="A pony",
            answer="a",
            explanation="It’s **the ORM**.",
        )
        cls.q2 = Question.objects.create(
            quiz=cls.quiz,
            order=2,
            text="What is a pony?",
            choice_a="A horse",
            choice_b="A pegasus",
            answer="b",
        )

    def set_step(self, step):
        Quiz.objects.filter(pk=self.quiz.pk).update(step=step)

    def join(self, name="Alice"):
        """Join the live quiz as a player, returning them."""
        response = self.client.post(
            "/quizzes/quiz-2026/live/join/", {"name": name}, headers=HTMX_HEADERS
        )
        assert response.status_code == HTTPStatus.OK
        return Player.objects.get(name=name)

    def login_organizer(self):
        User.objects.create_user("organizer", password="thames", is_staff=True)
        self.client.login(username="organizer", password="thames")


class QuizListTests(QuizTestCase):
    def test_success(self):
        Quiz.objects.create(
            slug="secret", title="Secret Quiz", date=dt.date(2026, 12, 9)
        )

        response = self.client.get("/quizzes/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>Quizzes | Django London</title>" in response.text
        assert "/quizzes/quiz-2026/" in response.text
        assert "December 2026, 2 questions" in response.text
        # Unpublished quizzes stay secret until they have been played.
        assert "Secret Quiz" not in response.text

    def test_imported_quizzes(self):
        response = self.client.get("/quizzes/")

        assert "/quizzes/django-quiz-2025/" in response.text

    def test_empty(self):
        Quiz.objects.all().delete()

        response = self.client.get("/quizzes/")

        assert "No quizzes yet." in response.text


class QuizDetailTests(QuizTestCase):
    def test_success(self):
        response = self.client.get("/quizzes/quiz-2026/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>Django Quiz 2026 | Django London</title>" in response.text
        assert '<a href="/meetups/">December meetup</a>' in response.text
        assert "What is <code>django.db</code>?" in response.text
        assert f"name=question-{self.q1.pk} value=c" in response.text
        assert "Check my answers" in response.text
        # The answers stay hidden until the end.
        assert "the ORM</strong>" not in response.text

    def test_not_found(self):
        response = self.client.get("/quizzes/does-not-exist/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unpublished(self):
        Quiz.objects.filter(pk=self.quiz.pk).update(published=False)

        response = self.client.get("/quizzes/quiz-2026/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unpublished_preview_for_organizers(self):
        Quiz.objects.filter(pk=self.quiz.pk).update(published=False)
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/")

        assert response.status_code == HTTPStatus.OK

    def test_submit(self):
        response = self.client.post(
            "/quizzes/quiz-2026/",
            {f"question-{self.q1.pk}": "a", f"question-{self.q2.pk}": "a"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        # Only the results, to swap in for the form.
        assert "<title>" not in response.text
        assert "You scored 1/2" in response.text
        assert "perfect" not in response.text
        assert "✓ Your answer" in response.text
        assert "✗ Your answer" in response.text
        assert "It’s <strong>the ORM</strong>." in response.text
        assert [r["correct"] for r in response.context["results"]] == [True, False]

    def test_submit_perfect(self):
        response = self.client.post(
            "/quizzes/quiz-2026/",
            {f"question-{self.q1.pk}": "a", f"question-{self.q2.pk}": "b"},
            headers=HTMX_HEADERS,
        )

        assert "You scored 2/2 — perfect!" in response.text

    def test_submit_unanswered_and_invalid(self):
        response = self.client.post(
            "/quizzes/quiz-2026/",
            {f"question-{self.q2.pk}": "z"},
            headers=HTMX_HEADERS,
        )

        assert "You scored 0/2" in response.text
        assert response.text.count("You didn’t answer this one.") == 2
        assert [r["chosen"] for r in response.context["results"]] == [None, None]

    def test_submit_without_htmx(self):
        response = self.client.post(
            "/quizzes/quiz-2026/", {f"question-{self.q1.pk}": "a"}
        )

        assert response.status_code == HTTPStatus.OK
        assert "<title>Django Quiz 2026 | Django London</title>" in response.text
        assert "You scored 1/2" in response.text

    def test_method_not_allowed(self):
        response = self.client.put("/quizzes/quiz-2026/")

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


class QuizLiveTests(QuizTestCase):
    def test_success(self):
        response = self.client.get("/quizzes/quiz-2026/live/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>Django Quiz 2026 | Django London</title>" in response.text
        assert "Join the quiz" in response.text
        assert "/static/django_htmx/htmx-4.min.js" in response.text
        # Nothing to follow until the player joins.
        assert "hx-get=" not in response.text

    def test_unpublished(self):
        # Live quizzes are played before they are published.
        Quiz.objects.filter(pk=self.quiz.pk).update(published=False)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert response.status_code == HTTPStatus.OK

    def test_not_found(self):
        response = self.client.get("/quizzes/does-not-exist/live/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_join_late(self):
        self.set_step(2)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "Join the quiz" in response.text
        assert "you can still join for the rest of it" in response.text

    def test_too_late_to_join(self):
        self.set_step(3)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "Join the quiz" not in response.text
        assert "it’s too late to join" in response.text

    def test_lobby(self):
        self.join()

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "You’re in, Alice!" in response.text
        assert "hx-get=/quizzes/quiz-2026/live/status/" in response.text
        assert 'hx-trigger="every 3s"' in response.text

    def test_question(self):
        self.join()
        self.set_step(1)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "Question 1 of 2" in response.text
        assert "What is <code>django.db</code>?" in response.text
        assert "name=choice value=c" in response.text
        assert f"name=question value={self.q1.pk}" in response.text
        assert "Tap your answer." in response.text
        assert 'hx-trigger="every 2s"' in response.text

    def test_question_answered(self):
        player = self.join()
        Answer.objects.create(player=player, question=self.q1, choice="b")
        self.set_step(1)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "You chose <strong>B</strong>." in response.text
        assert "aria-pressed=true" in response.text

    def test_reveal_correct(self):
        player = self.join()
        Answer.objects.create(player=player, question=self.q1, choice="a")
        self.set_step(3)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "Answer 1 of 2" in response.text
        assert "✓ Correct!" in response.text
        assert "1/1 so far." in response.text

    def test_reveal_incorrect(self):
        player = self.join()
        Answer.objects.create(player=player, question=self.q1, choice="b")
        self.set_step(3)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "✗ Not this time" in response.text
        assert "You chose <strong>B</strong>, but the answer was" in response.text
        assert "0/1 so far." in response.text

    def test_reveal_unanswered(self):
        self.join()
        self.set_step(3)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "✗ No answer" in response.text
        assert "The answer was <strong>A</strong>." in response.text

    def test_results(self):
        player = self.join()
        Answer.objects.create(player=player, question=self.q1, choice="a")
        self.set_step(5)

        response = self.client.get("/quizzes/quiz-2026/live/")

        assert "You scored 1/2" in response.text
        # Nothing more for the phone to show.
        assert "hx-get=" not in response.text


class QuizLiveStatusTests(QuizTestCase):
    def test_success(self):
        self.join()

        response = self.client.get(
            "/quizzes/quiz-2026/live/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "<title>" not in response.text
        assert "You’re in, Alice!" in response.text

    def test_removed_player(self):
        self.join().delete()

        response = self.client.get(
            "/quizzes/quiz-2026/live/status/", headers=HTMX_HEADERS
        )

        assert "Join the quiz" in response.text


class QuizLiveJoinTests(QuizTestCase):
    def test_success(self):
        response = self.client.post(
            "/quizzes/quiz-2026/live/join/", {"name": "Alice"}, headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "You’re in, Alice!" in response.text
        player = Player.objects.get()
        assert player.quiz == self.quiz
        assert self.client.session[f"quiz_player_{self.quiz.pk}"] == player.pk

    def test_invalid(self):
        response = self.client.post(
            "/quizzes/quiz-2026/live/join/", {"name": ""}, headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert "This field is required." in response.text
        assert not Player.objects.exists()

    def test_without_htmx_redirects(self):
        response = self.client.post("/quizzes/quiz-2026/live/join/", {"name": "Alice"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/quizzes/quiz-2026/live/"
        assert not Player.objects.exists()

    def test_twice_does_not_create_a_second_player(self):
        self.join()

        response = self.client.post(
            "/quizzes/quiz-2026/live/join/",
            {"name": "Alice Again"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        assert Player.objects.count() == 1

    def test_too_late(self):
        self.set_step(3)

        response = self.client.post(
            "/quizzes/quiz-2026/live/join/", {"name": "Alice"}, headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "it’s too late to join" in response.text
        assert not Player.objects.exists()

    def test_get_not_allowed(self):
        response = self.client.get("/quizzes/quiz-2026/live/join/")

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


class QuizLiveAnswerTests(QuizTestCase):
    def post_answer(self, choice, question=None, **kwargs):
        question = question or self.q1
        return self.client.post(
            "/quizzes/quiz-2026/live/answer/",
            {"question": question.pk, "choice": choice},
            **kwargs,
        )

    def test_success(self):
        player = self.join()
        self.set_step(1)

        response = self.post_answer("c", headers=HTMX_HEADERS)

        assert response.status_code == HTTPStatus.OK
        assert "You chose <strong>C</strong>." in response.text
        assert Answer.objects.get().player == player

    def test_change_of_mind(self):
        self.join()
        self.set_step(1)
        self.post_answer("c", headers=HTMX_HEADERS)

        response = self.post_answer("a", headers=HTMX_HEADERS)

        assert "You chose <strong>A</strong>." in response.text
        assert Answer.objects.get().choice == "a"

    def test_question_closed(self):
        # The quizmaster moved on just before the tap landed.
        self.join()
        self.set_step(2)

        response = self.post_answer("c", headers=HTMX_HEADERS)

        assert response.status_code == HTTPStatus.OK
        assert "Question 2 of 2" in response.text
        assert not Answer.objects.exists()

    def test_not_a_choice(self):
        self.join()
        self.set_step(2)

        self.post_answer("c", question=self.q2, headers=HTMX_HEADERS)

        assert not Answer.objects.exists()

    def test_outside_a_question(self):
        self.join()

        response = self.post_answer("a", headers=HTMX_HEADERS)

        assert "You’re in, Alice!" in response.text
        assert not Answer.objects.exists()

    def test_not_joined(self):
        self.set_step(1)

        response = self.post_answer("a", headers=HTMX_HEADERS)

        assert response.status_code == HTTPStatus.OK
        assert "Join the quiz" in response.text
        assert not Answer.objects.exists()

    def test_without_htmx_redirects(self):
        self.join()
        self.set_step(1)

        response = self.post_answer("a")

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/quizzes/quiz-2026/live/"
        assert not Answer.objects.exists()


class QuizScreenTests(QuizTestCase):
    def test_requires_staff(self):
        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"].startswith("/organizers-admin/login/")

    def test_not_found(self):
        self.login_organizer()

        response = self.client.get("/quizzes/does-not-exist/screen/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_lobby(self):
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>Django Quiz 2026 | Django London</title>" in response.text
        assert "<svg" in response.text
        assert "http://testserver/quizzes/quiz-2026/live/" in response.text
        assert "0 players" in response.text
        assert "Waiting for players…" in response.text
        assert "Start the quiz" in response.text
        assert "Back</button>" not in response.text
        assert "Start over" not in response.text

    def test_lobby_with_players(self):
        self.join()
        self.client.logout()
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "1 player" in response.text
        assert "Remove Alice" in response.text
        assert "Start over" in response.text

    def test_question(self):
        alice = self.join()
        bob = Player.objects.create(quiz=self.quiz, name="Bob")
        Answer.objects.create(player=alice, question=self.q1, choice="a")
        Answer.objects.create(player=bob, question=self.q1, choice="b")
        Answer.objects.create(player=bob, question=self.q2, choice="b")
        self.set_step(2)
        self.client.logout()
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "Question 2 of 2" in response.text
        assert "What is a pony?" in response.text
        assert "1 of 2 answered" in response.text
        assert "In the lead" in response.text
        assert "Catching up" in response.text
        assert "Reveal the answers" in response.text
        assert "Back</button>" in response.text

    def test_question_without_standings(self):
        self.set_step(2)
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "In the lead" not in response.text

    def test_standing_with_more(self):
        for i in range(10):
            player = Player.objects.create(quiz=self.quiz, name=f"Player {i}")
            Answer.objects.create(player=player, question=self.q1, choice="a")
        Player.objects.create(quiz=self.quiz, name="Bob")
        self.set_step(2)
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "Player 7 and 2 more" in response.text

    def test_reveal(self):
        player = self.join()
        Answer.objects.create(player=player, question=self.q1, choice="a")
        self.set_step(3)
        self.client.logout()
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "Answer 1 of 2" in response.text
        assert "quiz-letter-a correct" in response.text
        assert "It’s <strong>the ORM</strong>." in response.text
        assert "Next answer" in response.text

    def test_reveal_without_explanation(self):
        self.set_step(4)
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "quiz-explanation" not in response.text
        assert "Show the results" in response.text

    def test_results(self):
        alice = self.join()
        Answer.objects.create(player=alice, question=self.q1, choice="a")
        Player.objects.create(quiz=self.quiz, name="Bob")
        Player.objects.create(quiz=self.quiz, name="Carol")
        self.set_step(5)
        self.client.logout()
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "Django Quiz 2026: results" in response.text
        assert "<p class=quiz-tier-score>1/2</p>" in response.text
        assert "<li>Alice</li>" in response.text
        assert "Bob" not in response.text
        assert "Show 0/2" in response.text
        assert "Start over" in response.text

    def test_results_last_tier(self):
        alice = self.join()
        Answer.objects.create(player=alice, question=self.q1, choice="a")
        Player.objects.create(quiz=self.quiz, name="Bob")
        Player.objects.create(quiz=self.quiz, name="Carol")
        self.set_step(6)
        self.client.logout()
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "<p class=quiz-tier-score>0/2</p>" in response.text
        assert "<li>Bob</li><li>Carol</li>" in response.text
        assert "<strong>1/2</strong> Alice" in response.text
        assert "That’s everyone." in response.text

    def test_results_nobody_played(self):
        self.set_step(5)
        self.login_organizer()

        response = self.client.get("/quizzes/quiz-2026/screen/")

        assert "Nobody played!" in response.text


class QuizScreenStatusTests(QuizTestCase):
    def test_requires_staff(self):
        response = self.client.get("/quizzes/quiz-2026/screen/status/")

        assert response.status_code == HTTPStatus.FOUND

    def test_success(self):
        self.login_organizer()

        response = self.client.get(
            "/quizzes/quiz-2026/screen/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "<title>" not in response.text
        assert "0 players" in response.text


class QuizScreenNextTests(QuizTestCase):
    def test_requires_staff(self):
        response = self.client.post("/quizzes/quiz-2026/screen/next/", {"step": 0})

        assert response.status_code == HTTPStatus.FOUND
        self.quiz.refresh_from_db()
        assert self.quiz.step == 0

    def test_success(self):
        self.login_organizer()

        response = self.client.post(
            "/quizzes/quiz-2026/screen/next/", {"step": 0}, headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Question 1 of 2" in response.text
        self.quiz.refresh_from_db()
        assert self.quiz.step == 1

    def test_double_press(self):
        self.login_organizer()
        self.client.post(
            "/quizzes/quiz-2026/screen/next/", {"step": 0}, headers=HTMX_HEADERS
        )

        response = self.client.post(
            "/quizzes/quiz-2026/screen/next/", {"step": 0}, headers=HTMX_HEADERS
        )

        assert "Question 1 of 2" in response.text
        self.quiz.refresh_from_db()
        assert self.quiz.step == 1

    def test_at_the_end(self):
        self.set_step(5)
        self.login_organizer()

        self.client.post(
            "/quizzes/quiz-2026/screen/next/", {"step": 5}, headers=HTMX_HEADERS
        )

        self.quiz.refresh_from_db()
        assert self.quiz.step == 5

    def test_invalid_step(self):
        self.login_organizer()

        response = self.client.post(
            "/quizzes/quiz-2026/screen/next/", {"step": "x"}, headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        self.quiz.refresh_from_db()
        assert self.quiz.step == 0

    def test_without_htmx_redirects(self):
        self.login_organizer()

        response = self.client.post("/quizzes/quiz-2026/screen/next/", {"step": 0})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/quizzes/quiz-2026/screen/"
        self.quiz.refresh_from_db()
        assert self.quiz.step == 1


class QuizScreenBackTests(QuizTestCase):
    def test_requires_staff(self):
        self.set_step(1)

        response = self.client.post("/quizzes/quiz-2026/screen/back/", {"step": 1})

        assert response.status_code == HTTPStatus.FOUND
        self.quiz.refresh_from_db()
        assert self.quiz.step == 1

    def test_success(self):
        self.set_step(1)
        self.login_organizer()

        response = self.client.post(
            "/quizzes/quiz-2026/screen/back/", {"step": 1}, headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Start the quiz" in response.text
        self.quiz.refresh_from_db()
        assert self.quiz.step == 0

    def test_at_the_start(self):
        self.login_organizer()

        self.client.post(
            "/quizzes/quiz-2026/screen/back/", {"step": 0}, headers=HTMX_HEADERS
        )

        self.quiz.refresh_from_db()
        assert self.quiz.step == 0

    def test_without_step(self):
        self.set_step(1)
        self.login_organizer()

        self.client.post("/quizzes/quiz-2026/screen/back/", headers=HTMX_HEADERS)

        self.quiz.refresh_from_db()
        assert self.quiz.step == 1

    def test_without_htmx_redirects(self):
        self.set_step(1)
        self.login_organizer()

        response = self.client.post("/quizzes/quiz-2026/screen/back/", {"step": 1})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/quizzes/quiz-2026/screen/"


class QuizScreenResetTests(QuizTestCase):
    def test_requires_staff(self):
        self.join()

        response = self.client.post("/quizzes/quiz-2026/screen/reset/")

        assert response.status_code == HTTPStatus.FOUND
        assert Player.objects.exists()

    def test_success(self):
        self.join()
        self.set_step(5)
        self.client.logout()
        self.login_organizer()

        response = self.client.post(
            "/quizzes/quiz-2026/screen/reset/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "0 players" in response.text
        assert not Player.objects.exists()
        self.quiz.refresh_from_db()
        assert self.quiz.step == 0

    def test_without_htmx_redirects(self):
        self.login_organizer()

        response = self.client.post("/quizzes/quiz-2026/screen/reset/")

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/quizzes/quiz-2026/screen/"


class QuizScreenRemovePlayerTests(QuizTestCase):
    def remove_url(self, player):
        return f"/quizzes/quiz-2026/screen/players/{player.pk}/remove/"

    def test_requires_staff(self):
        player = self.join()

        response = self.client.post(self.remove_url(player))

        assert response.status_code == HTTPStatus.FOUND
        assert Player.objects.filter(pk=player.pk).exists()

    def test_success(self):
        player = self.join()
        self.client.logout()
        self.login_organizer()

        response = self.client.post(self.remove_url(player), headers=HTMX_HEADERS)

        assert response.status_code == HTTPStatus.OK
        assert "0 players" in response.text
        assert not Player.objects.exists()

    def test_without_htmx_redirects(self):
        player = self.join()
        self.client.logout()
        self.login_organizer()

        response = self.client.post(self.remove_url(player))

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/quizzes/quiz-2026/screen/"
        assert not Player.objects.exists()
