from django.test import TestCase
from django.utils import timezone

from djangolondon.models import (
    Entry,
    Meetup,
    Prize,
    PrizeDraw,
    Speaker,
    Talk,
    voucher_upload_to,
)


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

    def test_voucher_upload_to(self):
        draw = PrizeDraw(slug="june-2026", name="June 2026 Draw")
        prize = Prize(draw=draw, name="Django Book")

        path = voucher_upload_to(prize, "voucher.pdf")

        assert path == "vouchers/june-2026/voucher.pdf"


class EntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.draw = PrizeDraw.objects.create(slug="june-2026", name="June 2026 Draw")

    def test_str(self):
        entry = Entry(name="Alice")
        assert str(entry) == "Alice"

    def test_won_prize_none(self):
        entry = Entry.objects.create(draw=self.draw, name="Alice")

        assert entry.won_prize() is None

    def test_won_prize(self):
        entry = Entry.objects.create(draw=self.draw, name="Alice")
        prize = Prize.objects.create(draw=self.draw, name="Book", winner=entry)

        assert entry.won_prize() == prize
