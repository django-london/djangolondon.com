from http import HTTPStatus

from django.test import TestCase


class IndexTests(TestCase):
    def test_success(self):
        response = self.client.get("/")
        assert response.status_code == HTTPStatus.OK
        assert len(response.context["meetups"]) <= 3
        assert "/meetups/" in response.text


class CodeOfConductTests(TestCase):
    def test_success(self):
        response = self.client.get("/code-of-conduct/")
        assert response.status_code == HTTPStatus.OK
        assert "<title>Code of Conduct | Django London</title>" in response.text
        assert "Be Awesome to Each Other" in response.text


class MeetupListTests(TestCase):
    def test_success(self):
        response = self.client.get("/meetups/")
        assert response.status_code == HTTPStatus.OK
        grouped = response.context["grouped_meetups"]
        years = [year for year, _ in grouped]
        assert years == sorted(years, reverse=True)
        assert len(years) == len(set(years))
        assert "/meetups/2021-05-18/" in response.text


class MeetupDetailTests(TestCase):
    def test_success(self):
        response = self.client.get("/meetups/2021-05-18/")
        assert response.status_code == HTTPStatus.OK
        assert "May Django Meetup" in response.text
        assert "Maps with Django" in response.text
        assert "Paolo Melchiorre" in response.text

    def test_not_found(self):
        response = self.client.get("/meetups/2000-01-01/")
        assert response.status_code == HTTPStatus.NOT_FOUND


class MeetupRedirectTests(TestCase):
    def test_redirect(self):
        response = self.client.get("/meetup/2021-05-18/")
        assert response.status_code == HTTPStatus.MOVED_PERMANENTLY
        assert response["Location"] == "/meetups/2021-05-18/"


class FaviconTests(TestCase):
    def test_success(self):
        response = self.client.get("/favicon.ico")
        assert response.status_code == HTTPStatus.OK
