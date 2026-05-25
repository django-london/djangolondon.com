import os
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
from unittest import mock

from django.test import SimpleTestCase

from djangolondon import settings


class SettingsTests(SimpleTestCase):
    def reimport_settings(self, name: str) -> ModuleType:
        spec = spec_from_file_location(f"{__name__}.{name}", settings.__file__)
        module = module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module

    def test_normal(self) -> None:
        self.reimport_settings("normal")

    def test_https(self) -> None:
        with mock.patch.dict(os.environ, {"HTTPS": "1"}):
            module = self.reimport_settings("https")
        assert module.SECURE_SSL_REDIRECT
