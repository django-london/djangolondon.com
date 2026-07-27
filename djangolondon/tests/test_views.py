from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from djangolondon.models import Entry, Prize, PrizeDraw, Speaker


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


class MeetupSlidesTests(TestCase):
    def test_success(self):
        response = self.client.get("/slides/2018-10-09/django-sql.pdf")
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "application/pdf"

    def test_not_found(self):
        response = self.client.get("/slides/2018-10-09/does-not-exist.pdf")
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


HTMX_HEADERS = {"HX-Request": "true"}


class PrizeDrawTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")
        cls.prize = Prize.objects.create(draw=cls.draw, name="Django Book")

    def enter(self, name="Alice"):
        """Enter the draw as an attendee, returning their entry."""
        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": name},
            headers=HTMX_HEADERS,
        )
        assert response.status_code == HTTPStatus.OK
        return Entry.objects.get(name=name)

    def login_organizer(self):
        User.objects.create_user("organizer", password="thames", is_staff=True)
        self.client.login(username="organizer", password="thames")


class PrizeDrawJoinTests(PrizeDrawTestCase):
    def test_success(self):
        response = self.client.get("/prize-draws/june-2026/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>June 2026 Draw | Django London</title>" in response.text
        assert "Enter the draw" in response.text
        assert "/static/django_htmx/htmx-4.min.js" in response.text

    def test_not_found(self):
        response = self.client.get("/prize-draws/does-not-exist/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_entries_closed(self):
        PrizeDraw.objects.filter(pk=self.draw.pk).update(entries_open=False)

        response = self.client.get("/prize-draws/june-2026/")

        assert response.status_code == HTTPStatus.OK
        assert "Entries are closed" in response.text

    def test_already_entered(self):
        self.enter()

        response = self.client.get("/prize-draws/june-2026/")

        assert response.status_code == HTTPStatus.OK
        assert "You’re in the draw, Alice." in response.text
        assert "hx-get=/prize-draws/june-2026/status/" in response.text


class PrizeDrawEnterTests(PrizeDrawTestCase):
    def test_success(self):
        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": "Alice"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        assert "You’re in the draw, Alice." in response.text
        entry = Entry.objects.get()
        assert entry.draw == self.draw
        assert entry.name == "Alice"
        assert self.client.session[f"prize_draw_entry_{self.draw.pk}"] == entry.pk

    def test_invalid(self):
        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": ""},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert "This field is required." in response.text
        assert not Entry.objects.exists()

    def test_without_htmx_redirects(self):
        response = self.client.post("/prize-draws/june-2026/enter/", {"name": "Alice"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/prize-draws/june-2026/"
        assert not Entry.objects.exists()

    def test_twice_does_not_create_a_second_entry(self):
        self.enter()

        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": "Alice Again"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        assert Entry.objects.count() == 1

    def test_entries_closed(self):
        PrizeDraw.objects.filter(pk=self.draw.pk).update(entries_open=False)

        response = self.client.post(
            "/prize-draws/june-2026/enter/",
            {"name": "Alice"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == HTTPStatus.OK
        assert "Entries are closed" in response.text
        assert not Entry.objects.exists()

    def test_get_not_allowed(self):
        response = self.client.get("/prize-draws/june-2026/enter/")

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


class PrizeDrawStatusTests(PrizeDrawTestCase):
    def test_waiting(self):
        self.enter()

        response = self.client.get(
            "/prize-draws/june-2026/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "You’re in the draw, Alice." in response.text

    def test_won(self):
        entry = self.enter()
        self.draw.draw_prize()

        response = self.client.get(
            "/prize-draws/june-2026/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "You won!" in response.text
        assert "Django Book" in response.text
        assert "Come and see an organizer to collect it." in response.text
        # Winners have no more news to wait for.
        assert "hx-get=" not in response.text
        assert self.prize.pk == entry.prize.pk

    def test_lost(self):
        self.enter()
        Entry.objects.create(draw=self.draw, name="Bob")
        self.prize.winner = Entry.objects.get(name="Bob")
        self.prize.save()

        response = self.client.get(
            "/prize-draws/june-2026/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "you didn’t win this time" in response.text
        assert "hx-get=" not in response.text

    def test_not_found(self):
        response = self.client.get("/prize-draws/does-not-exist/status/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class PrizeDrawScreenTests(PrizeDrawTestCase):
    def test_requires_staff(self):
        response = self.client.get("/prize-draws/june-2026/screen/")

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"].startswith("/organizers/login/")

    def test_success(self):
        self.login_organizer()

        response = self.client.get("/prize-draws/june-2026/screen/")

        assert response.status_code == HTTPStatus.OK
        assert "<title>June 2026 Draw | Django London</title>" in response.text
        assert "<svg" in response.text
        assert "http://testserver/prize-draws/june-2026/" in response.text
        assert "Draw Django Book" in response.text
        assert "0 entries" in response.text
        # Nobody has entered yet, so there is nobody to draw.
        assert "disabled" in response.text

    def test_not_found(self):
        self.login_organizer()

        response = self.client.get("/prize-draws/does-not-exist/screen/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class PrizeDrawScreenStatusTests(PrizeDrawTestCase):
    def test_requires_staff(self):
        response = self.client.get("/prize-draws/june-2026/screen/status/")

        assert response.status_code == HTTPStatus.FOUND

    def test_success(self):
        self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.get(
            "/prize-draws/june-2026/screen/status/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "1 entry" in response.text
        assert "disabled" not in response.text


class PrizeDrawDrawTests(PrizeDrawTestCase):
    def test_requires_staff(self):
        response = self.client.post("/prize-draws/june-2026/screen/draw/")

        assert response.status_code == HTTPStatus.FOUND
        assert not Prize.objects.filter(winner__isnull=False).exists()

    def test_success(self):
        self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.post(
            "/prize-draws/june-2026/screen/draw/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Winners" in response.text
        assert "Alice" in response.text
        assert "All prizes drawn!" in response.text
        self.prize.refresh_from_db()
        assert self.prize.winner == Entry.objects.get()

    def test_without_entries(self):
        self.login_organizer()

        response = self.client.post(
            "/prize-draws/june-2026/screen/draw/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Waiting for entries" in response.text
        self.prize.refresh_from_db()
        assert self.prize.winner is None

    def test_when_everyone_has_won(self):
        self.enter()
        self.client.logout()
        self.login_organizer()
        Prize.objects.create(draw=self.draw, order=2, name="Django Mug")
        self.draw.draw_prize()

        response = self.client.post(
            "/prize-draws/june-2026/screen/draw/", headers=HTMX_HEADERS
        )

        assert response.status_code == HTTPStatus.OK
        assert "Everyone in the draw has already won a prize." in response.text
        assert not Prize.objects.filter(name="Django Mug", winner__isnull=False)

    def test_without_htmx_redirects(self):
        self.enter()
        self.client.logout()
        self.login_organizer()

        response = self.client.post("/prize-draws/june-2026/screen/draw/")

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/prize-draws/june-2026/screen/"
        self.prize.refresh_from_db()
        assert self.prize.winner is not None


class PrizeVoucherTests(PrizeDrawTestCase):
    def attach_voucher(self):
        self.prize.voucher = SimpleUploadedFile(
            "django-book.pdf", b"%PDF-1.7 fake voucher"
        )
        self.prize.save()

    def test_success(self):
        self.attach_voucher()
        self.enter()
        self.draw.draw_prize()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.OK
        assert b"".join(response.streaming_content) == b"%PDF-1.7 fake voucher"
        assert "django-book.pdf" in response["Content-Disposition"]

    def test_without_voucher(self):
        self.enter()
        self.draw.draw_prize()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_without_entry(self):
        self.attach_voucher()
        Entry.objects.create(draw=self.draw, name="Bob")
        self.draw.draw_prize()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_for_someone_elses_prize(self):
        self.attach_voucher()
        self.enter()
        self.prize.winner = Entry.objects.create(draw=self.draw, name="Bob")
        self.prize.save()

        response = self.client.get(f"/prizes/{self.prize.pk}/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_not_found(self):
        response = self.client.get("/prizes/404/voucher/")

        assert response.status_code == HTTPStatus.NOT_FOUND


class MediaFileTests(TestCase):
    def setUp(self):
        self.path = settings.MEDIA_ROOT / "vouchers/june-2026/django-book.pdf"
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b"%PDF-1.7 fake voucher")

    def test_requires_staff(self):
        response = self.client.get("/media/vouchers/june-2026/django-book.pdf")

        assert response.status_code == HTTPStatus.FOUND

    def test_success(self):
        User.objects.create_user("organizer", password="thames", is_staff=True)
        self.client.login(username="organizer", password="thames")

        response = self.client.get("/media/vouchers/june-2026/django-book.pdf")

        assert response.status_code == HTTPStatus.OK
        assert b"".join(response.streaming_content) == b"%PDF-1.7 fake voucher"

    def test_not_found(self):
        User.objects.create_user("organizer", password="thames", is_staff=True)
        self.client.login(username="organizer", password="thames")

        response = self.client.get("/media/vouchers/does-not-exist.pdf")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_outside_media_root(self):
        User.objects.create_user("organizer", password="thames", is_staff=True)
        self.client.login(username="organizer", password="thames")

        response = self.client.get("/media/../settings.py")

        assert response.status_code == HTTPStatus.BAD_REQUEST
