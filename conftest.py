import pytest


@pytest.fixture(autouse=True)
def test_settings(settings):
    settings.STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    }
