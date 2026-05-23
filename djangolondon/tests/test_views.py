from http import HTTPStatus

from django.test import TestCase


class IndexTests(TestCase):
    def test_success(self):
        response = self.client.get("/")
        assert response.status_code == HTTPStatus.OK
        assert "May Django Meetup" in response.text


class CodeOfConductTests(TestCase):
    def test_success(self):
        response = self.client.get("/code-of-conduct/")
        assert response.status_code == HTTPStatus.OK
        assert "<title>Code of Conduct | Django London</title>" in response.text
        assert "Be Awesome to Each Other" in response.text


class MeetupTests(TestCase):
    def test_success(self):
        response = self.client.get("/meetups/2021-05-18/")
        assert response.status_code == HTTPStatus.OK
        assert "May Django Meetup" in response.text
        assert "Maps with Django" in response.text
        assert "Paolo Melchiorre" in response.text


class FaviconTests(TestCase):
    def test_success(self):
        response = self.client.get("/favicon.ico")
        assert response.status_code == HTTPStatus.OK
