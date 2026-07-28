import secrets

from django.db import models
from django.utils import timezone


class Speaker(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    github_username = models.CharField(max_length=200, blank=True)
    mastodon_url = models.URLField(blank=True)
    bluesky_handle = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class Meetup(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateTimeField()
    meetup_url = models.URLField(blank=True)
    skills_matter_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.title


class Talk(models.Model):
    meetup = models.ForeignKey(Meetup, on_delete=models.CASCADE)
    speakers = models.ManyToManyField(Speaker)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    blogpost_url = models.URLField(blank=True)
    slides_url = models.URLField(blank=True)
    skills_matter_url = models.URLField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["meetup", "title"],
                name="%(app_label)s_%(class)s_unique_talk",
            ),
        ]

    def __str__(self):
        return self.title


class PrizeDraw(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    entries_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name

    def next_prize(self):
        return self.prizes.defer("voucher").filter(winner=None).first()

    def eligible_entries(self):
        # Nobody wins twice in the same draw.
        return self.entries.filter(prize=None)

    def draw_prize(self):
        """
        Award the next undrawn prize to a random eligible entry.

        Returns the prize, or None if there was nothing to draw.
        """
        prize = self.next_prize()
        if prize is None:
            return None
        entries = list(self.eligible_entries())
        if not entries:
            return None

        winner = secrets.choice(entries)
        drawn_at = timezone.now()
        # Conditional update, so that two presses of the draw button cannot
        # both award this prize: whichever lands second draws nothing.
        if not self.prizes.filter(pk=prize.pk, winner=None).update(
            winner=winner, drawn_at=drawn_at
        ):
            return None
        prize.winner = winner
        prize.drawn_at = drawn_at

        if self.entries_open:
            self.entries_open = False
            self.save(update_fields=["entries_open"])

        return prize


class Prize(models.Model):
    draw = models.ForeignKey(
        PrizeDraw,
        on_delete=models.CASCADE,
        related_name="prizes",
    )
    order = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Vouchers live in the database: the deployment has no durable disk, and
    # this way they are covered by the same replication as everything else.
    voucher = models.BinaryField(blank=True)
    voucher_filename = models.CharField(max_length=200, blank=True)
    winner = models.OneToOneField(
        "Entry",
        on_delete=models.SET_NULL,
        related_name="prize",
        blank=True,
        null=True,
    )
    drawn_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class Entry(models.Model):
    draw = models.ForeignKey(
        PrizeDraw,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name_plural = "entries"

    def __str__(self):
        return self.name
