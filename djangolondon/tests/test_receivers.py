import datetime as dt
import tempfile
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from djangolondon.models import Meetup, Question, Quiz, Speaker, Talk
from djangolondon.receivers import (
    _dev_credentials,
    create_dev_superuser,
    load_quiz,
    load_static_data,
)


class DevCredentialsTests(TestCase):
    def test_returns_credentials_from_readme(self):
        username, password = _dev_credentials()
        assert username == "admin"
        assert password == "thames"


class CreateDevSuperuserTests(TestCase):
    def _call(self, app_name="djangolondon"):
        create_dev_superuser(sender=apps.get_app_config(app_name))

    @override_settings(DEBUG=True)
    def test_creates_superuser(self):
        self._call()
        user = User.objects.get(username="admin")
        assert user.is_staff
        assert user.is_superuser
        assert user.check_password("thames")

    @override_settings(DEBUG=True)
    def test_idempotent(self):
        self._call()
        self._call()
        assert User.objects.filter(username="admin").count() == 1

    @override_settings(DEBUG=False)
    def test_skipped_when_not_debug(self):
        self._call()
        assert not User.objects.filter(username="admin").exists()

    @override_settings(DEBUG=True)
    def test_skipped_for_other_apps(self):
        self._call(app_name="auth")
        assert not User.objects.filter(username="admin").exists()


class LoadStaticDataTests(TestCase):
    def setUp(self):
        Meetup.objects.all().delete()

    def _call(self, app_name="djangolondon"):
        load_static_data(sender=apps.get_app_config(app_name))

    def _call_with_dirs(self, tmp_path, speakers_toml, meetup_toml):
        speakers_dir = Path(tmp_path) / "speakers"
        speakers_dir.mkdir(exist_ok=True)
        for slug, content in speakers_toml.items():
            (speakers_dir / f"{slug}.toml").write_text(content)
        meetups_dir = Path(tmp_path) / "meetups"
        meetups_dir.mkdir(exist_ok=True)
        (meetups_dir / "2024-01-01.toml").write_text(meetup_toml)
        with (
            mock.patch("djangolondon.receivers.SPEAKERS_DIR", speakers_dir),
            mock.patch("djangolondon.receivers.DATA_DIR", meetups_dir),
        ):
            load_static_data(sender=apps.get_app_config("djangolondon"))

    def test_loads_meetups(self):
        self._call()
        assert Meetup.objects.exists()

    def test_idempotent(self):
        self._call()
        count = Meetup.objects.count()
        self._call()
        assert Meetup.objects.count() == count

    def test_skipped_for_other_apps(self):
        self._call(app_name="auth")
        assert not Meetup.objects.exists()

    def test_syncs_updated_toml_fields(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            speakers = {"jane-doe": 'name = "Jane Doe"\n'}
            self._call_with_dirs(
                tmp_path,
                speakers,
                """
                date = 2024-01-01T18:00:00+00:00
                title = "January Meetup"

                [[talks]]
                title = "My Talk"
                description = "Original description"
                blogpost_url = "https://example.com/post1"
                slides_url = "https://example.com/slides1"
                skills_matter_url = ""
                speakers = ["jane-doe"]
            """,
            )
            self._call_with_dirs(
                tmp_path,
                speakers,
                """
                date = 2024-01-01T18:00:00+00:00
                title = "January Meetup Updated"
                meetup_url = "https://meetup.com/event"

                [[talks]]
                title = "My Talk"
                description = "Updated description"
                blogpost_url = "https://example.com/post2"
                slides_url = "https://example.com/slides2"
                skills_matter_url = ""
                speakers = ["jane-doe"]
            """,
            )

        meetup = Meetup.objects.get(date="2024-01-01T18:00:00+00:00")
        assert meetup.title == "January Meetup Updated"
        assert meetup.meetup_url == "https://meetup.com/event"

        talks = Talk.objects.filter(meetup=meetup)
        assert talks.count() == 1
        talk = talks.get()
        assert talk.title == "My Talk"
        assert talk.description == "Updated description"
        assert talk.blogpost_url == "https://example.com/post2"
        assert talk.slides_url == "https://example.com/slides2"

        assert Speaker.objects.filter(slug="jane-doe").count() == 1
        assert set(talk.speakers.values_list("slug", flat=True)) == {"jane-doe"}

    def test_talk_with_multiple_speakers(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            speakers = {
                "jane-doe": 'name = "Jane Doe"\n',
                "john-smith": 'name = "John Smith"\n',
            }
            meetup_toml = """
                date = 2024-01-01T18:00:00+00:00
                title = "January Meetup"

                [[talks]]
                title = "Joint Talk"
                speakers = ["jane-doe", "john-smith"]
            """
            self._call_with_dirs(tmp_path, speakers, meetup_toml)
            self._call_with_dirs(tmp_path, speakers, meetup_toml)

        meetup = Meetup.objects.get(date="2024-01-01T18:00:00+00:00")
        assert Talk.objects.filter(meetup=meetup).count() == 1
        talk = Talk.objects.get(meetup=meetup)
        assert set(talk.speakers.values_list("slug", flat=True)) == {
            "jane-doe",
            "john-smith",
        }

    def test_unknown_speaker_slug_raises(self):
        with (
            tempfile.TemporaryDirectory() as tmp_path,
            self.assertRaises(ValueError, msg="Unknown speaker slugs"),
        ):
            self._call_with_dirs(
                tmp_path,
                {},
                """
                    date = 2024-01-01T18:00:00+00:00
                    title = "January Meetup"

                    [[talks]]
                    title = "My Talk"
                    speakers = ["does-not-exist"]
                    """,
            )

    def test_syncs_speaker_fields(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            self._call_with_dirs(
                tmp_path,
                {"jane-doe": ('name = "Jane Doe"\ngithub_username = "janedoe"\n')},
                """
                date = 2024-01-01T18:00:00+00:00
                title = "January Meetup"

                [[talks]]
                title = "My Talk"
                speakers = ["jane-doe"]
                """,
            )

        speaker = Speaker.objects.get(slug="jane-doe")
        assert speaker.name == "Jane Doe"
        assert speaker.github_username == "janedoe"
        assert speaker.mastodon_url == ""
        assert speaker.bluesky_handle == ""


class LoadQuizzesTests(TestCase):
    def test_loads_data_files(self):
        quiz = Quiz.objects.get(slug="django-quiz-2025")

        assert quiz.title == "Django Quiz 2025"
        assert quiz.date == dt.date(2025, 12, 9)
        assert quiz.imported
        assert quiz.published
        assert quiz.questions.count() == 12
        question = quiz.questions.first()
        assert question.text == "How old is Django this year?"
        assert question.answer == "c"

    def test_every_data_file_is_valid(self):
        for question in Question.objects.filter(quiz__imported=True):
            question.full_clean()

    def test_loads_from_quizzes_dir(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            quizzes_dir = Path(tmp_path)
            (quizzes_dir / "test-quiz.toml").write_text(
                """
                title = "Test Quiz"
                date = 2026-12-08

                [[questions]]
                text = "Yes?"
                choices = ["Yes", "No"]
                answer = "a"
                """
            )
            with mock.patch("djangolondon.receivers.QUIZZES_DIR", quizzes_dir):
                load_static_data(sender=apps.get_app_config("djangolondon"))

        quiz = Quiz.objects.get(slug="test-quiz")
        assert quiz.description == ""
        assert quiz.questions.get().explanation == ""


class LoadQuizTests(TestCase):
    def data(self, **kwargs):
        return {
            "title": "Test Quiz",
            "date": dt.date(2026, 12, 8),
            "description": "A quiz.\n",
            "questions": [
                {
                    "text": "What is Django?",
                    "choices": ["A web framework", "A guitarist", "A pony"],
                    "answer": "a",
                    "explanation": "It’s a framework.\n",
                },
                {
                    "text": "What is a pony?",
                    "choices": ["A horse", "A pegasus"],
                    "answer": "b",
                },
            ],
        } | kwargs

    def test_creates(self):
        quiz = load_quiz("test-quiz", self.data())

        assert quiz.title == "Test Quiz"
        assert quiz.description == "A quiz."
        assert quiz.published
        q1, q2 = quiz.questions.all()
        assert q1.order == 1
        assert q1.choices() == [
            ("a", "A web framework"),
            ("b", "A guitarist"),
            ("c", "A pony"),
        ]
        assert q1.choice_d == ""
        assert q1.explanation == "It’s a framework."
        assert q2.answer == "b"

    def test_updates_in_place(self):
        quiz = load_quiz("test-quiz", self.data())
        question = quiz.questions.first()
        Quiz.objects.filter(pk=quiz.pk).update(published=False)
        data = self.data(title="Test Quiz Updated")
        data["questions"][0]["text"] = "What is Django, really?"
        del data["questions"][1]

        quiz = load_quiz("test-quiz", data)

        assert quiz.title == "Test Quiz Updated"
        # Publishing is left to the admin, once the quiz exists.
        assert not quiz.published
        assert list(quiz.questions.values_list("pk", "text")) == [
            (question.pk, "What is Django, really?")
        ]

    def test_too_few_choices(self):
        data = self.data()
        data["questions"][1]["choices"] = ["A horse"]

        with self.assertRaisesMessage(
            ValueError, "test-quiz question 2: needs two to four choices"
        ):
            load_quiz("test-quiz", data)

    def test_too_many_choices(self):
        data = self.data()
        data["questions"][0]["choices"] = ["1", "2", "3", "4", "5"]

        with self.assertRaisesMessage(
            ValueError, "test-quiz question 1: needs two to four choices"
        ):
            load_quiz("test-quiz", data)

    def test_answer_not_a_choice(self):
        data = self.data()
        data["questions"][1]["answer"] = "c"

        with self.assertRaisesMessage(
            ValueError, "test-quiz question 2: answer is not a choice"
        ):
            load_quiz("test-quiz", data)
