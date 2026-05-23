import datetime as dt

from django.test import SimpleTestCase

from djangolondon.urls import ISODateConverter


class ISODateConverterTests(SimpleTestCase):
    def setUp(self):
        self.converter = ISODateConverter()

    def test_to_python(self):
        assert self.converter.to_python("2021-05-18") == dt.date(2021, 5, 18)

    def test_to_python_invalid(self):
        with self.assertRaises(ValueError):
            self.converter.to_python("not-a-date")

    def test_to_url(self):
        assert self.converter.to_url(dt.date(2021, 5, 18)) == "2021-05-18"
