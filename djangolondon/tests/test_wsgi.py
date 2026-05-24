from django.test import SimpleTestCase

from djangolondon.wsgi import application


class WSGITests(SimpleTestCase):
    def test_application_is_callable(self):
        assert callable(application)
