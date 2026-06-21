from django.test import TestCase
from django.utils import timezone

from djangolondon.models import Meetup, Speaker, Talk


class SpeakerTests(TestCase):
    def test_str(self):
        speaker = Speaker(slug="jane-doe", name="Jane Doe")
        assert str(speaker) == "Jane Doe"


class MeetupTests(TestCase):
    def test_str(self):
        meetup = Meetup(title="Django London #1", date=timezone.now())
        assert str(meetup) == "Django London #1"


class TalkTests(TestCase):
    def test_str(self):
        meetup = Meetup.objects.create(title="Django London #1", date=timezone.now())
        talk = Talk.objects.create(meetup=meetup, title="My Talk")
        assert str(talk) == "My Talk"
