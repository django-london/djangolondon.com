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
