from http import HTTPStatus

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from djangolondon.admin import EntryInline, PrizeDrawAdmin, TalkAdmin, TalkInline
from djangolondon.models import Meetup, Prize, PrizeDraw, Speaker, Talk


class SpeakersDisplayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        meetup = Meetup.objects.create(title="Test Meetup", date=timezone.now())
        cls.talk = Talk.objects.create(meetup=meetup, title="Test Talk")
        s1 = Speaker.objects.create(slug="alice", name="Alice")
        s2 = Speaker.objects.create(slug="bob", name="Bob")
        cls.talk.speakers.set([s1, s2])

    def test_talk_admin_speakers_display(self):
        talk_admin = TalkAdmin(Talk, admin.site)
        result = talk_admin.speakers_display(self.talk)
        assert result == "Alice, Bob"

    def test_talk_inline_speakers_display(self):
        inline = TalkInline(Meetup, admin.site)
        result = inline.speakers_display(self.talk)
        assert result == "Alice, Bob"


class PrizeDrawAdminTests(TestCase):
    def test_screen_link(self):
        draw = PrizeDraw(slug="june-2026", name="June 2026 Draw")
        prize_draw_admin = PrizeDrawAdmin(PrizeDraw, admin.site)

        result = prize_draw_admin.screen_link(draw)

        assert result == '<a href="/prize-draws/june-2026/screen/">Run draw</a>'

    def test_entries_cannot_be_added(self):
        inline = EntryInline(PrizeDraw, admin.site)

        assert inline.has_add_permission(None, None) is False


class PrizeDrawAdminPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")
        cls.user = User.objects.create_superuser("organizer", password="thames")

    def setUp(self):
        self.client.force_login(self.user)

    def test_changelist(self):
        response = self.client.get("/organizers/djangolondon/prizedraw/")

        assert response.status_code == HTTPStatus.OK
        assert "/prize-draws/june-2026/screen/" in response.text

    def test_add(self):
        response = self.client.get("/organizers/djangolondon/prizedraw/add/")

        assert response.status_code == HTTPStatus.OK
        assert 'enctype="multipart/form-data"' in response.text

    def test_change_with_a_voucher(self):
        Prize.objects.create(
            draw=self.draw,
            name="Django Book",
            voucher=SimpleUploadedFile("django-book.pdf", b"%PDF-1.7 fake"),
        )

        response = self.client.get(
            f"/organizers/djangolondon/prizedraw/{self.draw.pk}/change/"
        )

        assert response.status_code == HTTPStatus.OK
        assert "/media/vouchers/june-2026/django-book.pdf" in response.text
