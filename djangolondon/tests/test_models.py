from django.test import TestCase
from django.urls import resolve
from django.utils import timezone

from djangolondon.models import Entry, Meetup, Prize, PrizeDraw, Speaker, Talk


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


class PrizeDrawTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")

    def test_str(self):
        assert str(self.draw) == "June 2026 Draw"

    def test_get_absolute_url(self):
        url = self.draw.get_absolute_url()
        assert url == f"/prize-draws/{self.draw.slug}/screen/"
        assert resolve(url).func.__name__ == "prize_draw_screen"

    def test_next_prize(self):
        second = Prize.objects.create(draw=self.draw, order=2, name="Second")
        first = Prize.objects.create(draw=self.draw, order=1, name="First")

        assert self.draw.next_prize() == first

        first.winner = Entry.objects.create(draw=self.draw, name="Alice")
        first.save()

        assert self.draw.next_prize() == second

    def test_next_prize_none_left(self):
        assert self.draw.next_prize() is None

    def test_eligible_entries_excludes_winners(self):
        alice = Entry.objects.create(draw=self.draw, name="Alice")
        bob = Entry.objects.create(draw=self.draw, name="Bob")
        Prize.objects.create(draw=self.draw, name="Book", winner=alice)

        assert list(self.draw.eligible_entries()) == [bob]

    def test_draw_prize(self):
        prize = Prize.objects.create(draw=self.draw, name="Book")
        alice = Entry.objects.create(draw=self.draw, name="Alice")

        drawn = self.draw.draw_prize()

        assert drawn == prize
        prize.refresh_from_db()
        assert prize.winner == alice
        assert prize.drawn_at is not None

    def test_draw_prize_closes_entries(self):
        Prize.objects.create(draw=self.draw, name="Book")
        Entry.objects.create(draw=self.draw, name="Alice")

        self.draw.draw_prize()

        assert self.draw.entries_open is False
        self.draw.refresh_from_db()
        assert self.draw.entries_open is False

    def test_draw_prize_no_prizes(self):
        Entry.objects.create(draw=self.draw, name="Alice")

        assert self.draw.draw_prize() is None

    def test_draw_prize_no_entries(self):
        Prize.objects.create(draw=self.draw, name="Book")

        assert self.draw.draw_prize() is None
        assert self.draw.entries_open is True

    def test_draw_prize_when_another_press_got_there_first(self):
        prize = Prize.objects.create(draw=self.draw, name="Book")
        alice = Entry.objects.create(draw=self.draw, name="Alice")
        Entry.objects.create(draw=self.draw, name="Bob")

        # Stand in for a second press landing between the read and the write.
        eligible_entries = self.draw.eligible_entries

        def concurrent_draw():
            Prize.objects.filter(pk=prize.pk).update(
                winner=alice, drawn_at=timezone.now()
            )
            return eligible_entries()

        self.draw.eligible_entries = concurrent_draw

        assert self.draw.draw_prize() is None
        # The press that got there first keeps the prize.
        prize.refresh_from_db()
        assert prize.winner == alice

    def test_draw_prize_never_picks_the_same_entry_twice(self):
        Prize.objects.create(draw=self.draw, order=1, name="Book")
        Prize.objects.create(draw=self.draw, order=2, name="Mug")
        Entry.objects.create(draw=self.draw, name="Alice")
        Entry.objects.create(draw=self.draw, name="Bob")

        first = self.draw.draw_prize()
        second = self.draw.draw_prize()

        assert first.winner != second.winner


class PrizeTests(TestCase):
    def test_str(self):
        prize = Prize(name="Django Book")
        assert str(prize) == "Django Book"


class EntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")

    def test_str(self):
        entry = Entry(name="Alice")
        assert str(entry) == "Alice"
