from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from djangolondon.models import Meetup
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
