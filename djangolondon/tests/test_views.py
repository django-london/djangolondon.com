from http import HTTPStatus

from django.test import TestCase

from djangolondon.models import Speaker


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
        assert "Django London has held" in response.text
        assert "/meetups/2021-05-18/" in response.text


class MeetupDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.speaker = Speaker.objects.get(slug="paolo-melchiorre")

    def test_success(self):
        response = self.client.get("/meetups/2021-05-18/")
        assert response.status_code == HTTPStatus.OK
        assert "May Django Meetup" in response.text
        assert "Maps with Django" in response.text
        assert f"/speakers/{self.speaker.slug}/" in response.text
        assert "Paolo Melchiorre" in response.text

    def test_not_found(self):
        response = self.client.get("/meetups/2000-01-01/")
        assert response.status_code == HTTPStatus.NOT_FOUND


class MeetupRedirectTests(TestCase):
    def test_redirect(self):
        response = self.client.get("/meetup/2021-05-18/")
        assert response.status_code == HTTPStatus.MOVED_PERMANENTLY
        assert response["Location"] == "/meetups/2021-05-18/"


class SpeakerListTests(TestCase):
    def test_success(self):
        response = self.client.get("/speakers/")
        assert response.status_code == HTTPStatus.OK
        assert "<title>Speakers | Django London</title>" in response.text
        assert "Django London has hosted" in response.text
        assert "/speakers/paolo-melchiorre/" in response.text


class SpeakerDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.speaker = Speaker.objects.get(slug="paolo-melchiorre")

    def test_success(self):
        response = self.client.get(f"/speakers/{self.speaker.slug}/")
        assert response.status_code == HTTPStatus.OK
        assert "<title>Paolo Melchiorre | Django London</title>" in response.text
        assert "Maps with Django" in response.text
        assert "/meetups/2021-05-18/" in response.text

    def test_not_found(self):
        response = self.client.get("/speakers/does-not-exist/")
        assert response.status_code == HTTPStatus.NOT_FOUND


class FaviconTests(TestCase):
    def test_success(self):
        response = self.client.get("/favicon.ico")
        assert response.status_code == HTTPStatus.OK


class AtprotoDidTests(TestCase):
    def test_success(self):
        response = self.client.get("/.well-known/atproto-did")
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/plain"
        assert response.text == "did:plc:r4l26ukwabszkecqnsv77jt3"
