import tempfile
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from djangolondon.models import Meetup, Speaker, Talk
from djangolondon.receivers import (
    _dev_credentials,
    create_dev_superuser,
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

    def _call_with_toml(self, tmp_path, toml_content):
        toml_file = Path(tmp_path) / "2024-01-01.toml"
        toml_file.write_text(toml_content)
        with mock.patch("djangolondon.receivers.DATA_DIR", Path(tmp_path)):
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
            self._call_with_toml(
                tmp_path,
                """
                date = 2024-01-01T18:00:00+00:00
                title = "January Meetup"

                [[talks]]
                title = "My Talk"
                description = "Original description"
                blogpost_url = "https://example.com/post1"
                slides_url = "https://example.com/slides1"
                skills_matter_url = ""

                [talks.speaker]
                name = "Jane Doe"
            """,
            )
            self._call_with_toml(
                tmp_path,
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

                [talks.speaker]
                name = "Jane Doe"
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

        assert Speaker.objects.filter(name="Jane Doe").count() == 1

    def test_speaker_with_two_talks(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            self._call_with_toml(
                tmp_path,
                """
                date = 2024-01-01T18:00:00+00:00
                title = "January Meetup"

                [[talks]]
                title = "First Talk"

                [talks.speaker]
                name = "Jane Doe"

                [[talks]]
                title = "Second Talk"

                [talks.speaker]
                name = "Jane Doe"
            """,
            )
            self._call_with_toml(
                tmp_path,
                """
                date = 2024-01-01T18:00:00+00:00
                title = "January Meetup"

                [[talks]]
                title = "First Talk"

                [talks.speaker]
                name = "Jane Doe"

                [[talks]]
                title = "Second Talk"

                [talks.speaker]
                name = "Jane Doe"
            """,
            )

        meetup = Meetup.objects.get(date="2024-01-01T18:00:00+00:00")
        assert Talk.objects.filter(meetup=meetup).count() == 2
        assert Speaker.objects.filter(name="Jane Doe").count() == 1
