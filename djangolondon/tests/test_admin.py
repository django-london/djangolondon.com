import datetime as dt
from http import HTTPStatus

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from djangolondon.admin import (
    EntryInline,
    PlayerInline,
    PrizeDrawAdmin,
    QuizAdmin,
    TalkAdmin,
    TalkInline,
)
from djangolondon.forms import PrizeForm
from djangolondon.models import Meetup, Prize, PrizeDraw, Question, Quiz, Speaker, Talk


class SpeakersDisplayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        meetup = Meetup.objects.create(title="Test Meetup", date=timezone.now())
        cls.talk = Talk.objects.create(meetup=meetup, title="Test Talk")
        s1 = Speaker.objects.create(slug="alice", name="Alice")
        s2 = Speaker.objects.create(slug="bob", name="Bob")
        cls.talk.speakers.set([s1, s2])

    def test_talk_admin_speakers_display(self):
        talk_admin = TalkAdmin(Talk, admin.site)
        result = talk_admin.speakers_display(self.talk)
        assert result == "Alice, Bob"

    def test_talk_inline_speakers_display(self):
        inline = TalkInline(Meetup, admin.site)
        result = inline.speakers_display(self.talk)
        assert result == "Alice, Bob"


class PrizeDrawAdminTests(TestCase):
    def test_screen_link(self):
        draw = PrizeDraw(slug="june-2026", name="June 2026 Draw")
        prize_draw_admin = PrizeDrawAdmin(PrizeDraw, admin.site)

        result = prize_draw_admin.screen_link(draw)

        assert result == '<a href="/prize-draws/june-2026/screen/">Run draw</a>'

    def test_entries_cannot_be_added(self):
        inline = EntryInline(PrizeDraw, admin.site)

        assert inline.has_add_permission(None, None) is False


class PrizeDrawAdminPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")
        cls.user = User.objects.create_superuser("organizer", password="thames")

    def setUp(self):
        self.client.force_login(self.user)

    def test_changelist(self):
        response = self.client.get("/organizers-admin/djangolondon/prizedraw/")

        assert response.status_code == HTTPStatus.OK
        assert "/prize-draws/june-2026/screen/" in response.text

    def test_add(self):
        response = self.client.get("/organizers-admin/djangolondon/prizedraw/add/")

        assert response.status_code == HTTPStatus.OK
        assert 'enctype="multipart/form-data"' in response.text

    def test_change_shows_the_attached_voucher(self):
        Prize.objects.create(
            draw=self.draw,
            name="Django Book",
            voucher=b"%PDF-1.7 fake",
            voucher_filename="django-book.pdf",
        )

        response = self.client.get(
            f"/organizers-admin/djangolondon/prizedraw/{self.draw.pk}/change/"
        )

        assert response.status_code == HTTPStatus.OK
        assert "django-book.pdf" in response.text


class PrizeFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")

    def build(self, upload):
        return PrizeForm(
            {"order": 1, "name": "Django Book", "description": ""},
            {"voucher_upload": upload} if upload is not None else {},
            instance=Prize(draw=self.draw),
        )

    def test_stores_the_upload_in_the_database(self):
        form = self.build(
            SimpleUploadedFile("django-book.pdf", b"%PDF-1.7 fake voucher")
        )

        assert form.is_valid(), form.errors
        prize = form.save()

        prize.refresh_from_db()
        assert bytes(prize.voucher) == b"%PDF-1.7 fake voucher"
        assert prize.voucher_filename == "django-book.pdf"

    def test_without_an_upload(self):
        form = self.build(None)

        assert form.is_valid(), form.errors
        prize = form.save()

        assert bytes(prize.voucher) == b""
        assert prize.voucher_filename == ""

    def test_keeps_the_current_voucher(self):
        prize = Prize.objects.create(
            draw=self.draw,
            name="Django Book",
            voucher=b"%PDF-1.7 fake voucher",
            voucher_filename="django-book.pdf",
        )
        form = PrizeForm(
            {"order": 1, "name": "Django Book", "description": ""},
            {},
            instance=prize,
        )

        assert form.is_valid(), form.errors
        form.save()

        prize.refresh_from_db()
        assert bytes(prize.voucher) == b"%PDF-1.7 fake voucher"

    def test_rejects_a_non_pdf(self):
        form = self.build(SimpleUploadedFile("voucher.txt", b"not a pdf"))

        assert not form.is_valid()
        assert "File extension “txt” is not allowed." in str(
            form.errors["voucher_upload"]
        )

    def test_rejects_an_oversized_upload(self):
        oversized = b"%PDF-1.7" + b"x" * PrizeForm.MAX_VOUCHER_SIZE
        form = self.build(SimpleUploadedFile("big.pdf", oversized))

        assert not form.is_valid()
        assert form.errors["voucher_upload"] == ["Vouchers must be 5 MB or smaller."]

    def test_save_without_committing(self):
        form = self.build(
            SimpleUploadedFile("django-book.pdf", b"%PDF-1.7 fake voucher")
        )

        assert form.is_valid(), form.errors
        prize = form.save(commit=False)

        assert prize.pk is None
        assert bytes(prize.voucher) == b"%PDF-1.7 fake voucher"


class QuizAdminTests(TestCase):
    def test_links(self):
        quiz = Quiz(slug="quiz-2026", title="Django Quiz 2026")
        quiz_admin = QuizAdmin(Quiz, admin.site)

        assert (
            quiz_admin.screen_link(quiz)
            == '<a href="/quizzes/quiz-2026/screen/">Run live</a>'
        )
        assert (
            quiz_admin.play_link(quiz) == '<a href="/quizzes/quiz-2026/">Play alone</a>'
        )

    def test_players_cannot_be_added(self):
        inline = PlayerInline(Quiz, admin.site)

        assert inline.has_add_permission(None, None) is False


class QuizAdminPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("organizer", password="thames")

    def setUp(self):
        self.client.force_login(self.user)

    def test_changelist(self):
        response = self.client.get("/organizers-admin/djangolondon/quiz/")

        assert response.status_code == HTTPStatus.OK
        assert "/quizzes/django-quiz-2025/screen/" in response.text

    def test_add(self):
        response = self.client.get("/organizers-admin/djangolondon/quiz/add/")

        assert response.status_code == HTTPStatus.OK
        assert 'name="questions-0-choice_d"' in response.text
        assert "data file" not in response.text

    def test_add_with_questions(self):
        response = self.client.post(
            "/organizers-admin/djangolondon/quiz/add/",
            {
                "slug": "quiz-2026",
                "title": "Django Quiz 2026",
                "date": "2026-12-08",
                "description": "",
                "questions-TOTAL_FORMS": "1",
                "questions-INITIAL_FORMS": "0",
                "questions-0-order": "1",
                "questions-0-text": "What is Django?",
                "questions-0-choice_a": "A web framework",
                "questions-0-choice_b": "A guitarist",
                "questions-0-choice_c": "",
                "questions-0-choice_d": "",
                "questions-0-answer": "a",
                "questions-0-explanation": "",
                "players-TOTAL_FORMS": "0",
                "players-INITIAL_FORMS": "0",
            },
        )

        assert response.status_code == HTTPStatus.FOUND, response.text
        quiz = Quiz.objects.get(slug="quiz-2026")
        assert not quiz.published
        assert not quiz.imported
        assert quiz.questions.get().choices() == [
            ("a", "A web framework"),
            ("b", "A guitarist"),
        ]

    def test_change(self):
        quiz = Quiz.objects.create(
            slug="quiz-2026", title="Django Quiz 2026", date=dt.date(2026, 12, 8)
        )
        Question.objects.create(
            quiz=quiz, text="What is Django?", choice_a="A", choice_b="B", answer="a"
        )

        response = self.client.get(
            f"/organizers-admin/djangolondon/quiz/{quiz.pk}/change/"
        )

        assert response.status_code == HTTPStatus.OK
        assert 'name="title"' in response.text
        assert 'name="questions-0-text"' in response.text

    def test_change_imported(self):
        quiz = Quiz.objects.get(slug="django-quiz-2025")

        response = self.client.get(
            f"/organizers-admin/djangolondon/quiz/{quiz.pk}/change/"
        )

        assert response.status_code == HTTPStatus.OK
        assert "<code>data/quizzes/django-quiz-2025.toml</code>" in response.text
        assert 'name="title"' not in response.text
        assert 'name="questions-0-text"' not in response.text
        # Publishing is still up to the organizers.
        assert 'name="published"' in response.text
