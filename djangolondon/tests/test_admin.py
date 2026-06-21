from django.contrib import admin
from django.test import TestCase
from django.utils import timezone

from djangolondon.admin import TalkAdmin, TalkInline
from djangolondon.models import Meetup, Speaker, Talk


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
