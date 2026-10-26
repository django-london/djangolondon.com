import secrets

from django.core.exceptions import ValidationError
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

    def get_absolute_url(self):
        return f"/prize-draws/{self.slug}/screen/"

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


class Quiz(models.Model):
    """
    A multiple choice quiz, played live at a meetup or alone afterwards.

    A live quiz is a series of steps that the quizmaster presses through:
    the lobby, each question in turn, each answer in turn, and then the players
    who reached each score, from the top down.
    """

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    date = models.DateField()
    description = models.TextField(blank=True, help_text="Markdown.")
    published = models.BooleanField(
        default=False,
        help_text=(
            "List the quiz on the site for anyone to play on their own. Leave"
            " this off until the quiz has been played live, so the answers stay"
            " secret."
        ),
    )
    # Quizzes from data/quizzes/ are refreshed from their files on every
    # migrate, so they can only be edited there.
    imported = models.BooleanField(default=False, editable=False)
    step = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name_plural = "quizzes"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f"/quizzes/{self.slug}/screen/"

    def advance(self, from_step: int, to_step: int) -> bool:
        """
        Move the live quiz from one step to another.

        Returns whether the quiz moved. Conditional, so that two presses of a
        button cannot both move it: whichever lands second does nothing.
        """
        moved = bool(
            Quiz.objects.filter(pk=self.pk, step=from_step).update(step=to_step)
        )
        if moved:
            self.step = to_step
        return moved

    def reset(self):
        """Clear out the players, ready to run the quiz live again."""
        self.players.all().delete()
        Quiz.objects.filter(pk=self.pk).update(step=0)
        self.step = 0


class Question(models.Model):
    LETTERS = "abcd"

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    order = models.PositiveIntegerField(default=0)
    text = models.TextField(help_text="Markdown, on one line.")
    choice_a = models.CharField("choice A", max_length=200)
    choice_b = models.CharField("choice B", max_length=200)
    choice_c = models.CharField("choice C", max_length=200, blank=True)
    choice_d = models.CharField("choice D", max_length=200, blank=True)
    answer = models.CharField(
        max_length=1,
        choices=[(letter, letter.upper()) for letter in LETTERS],
    )
    explanation = models.TextField(
        blank=True,
        help_text="Markdown, shown with the answer.",
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text

    def clean(self):
        filled = [bool(getattr(self, f"choice_{letter}")) for letter in self.LETTERS]
        if filled[2:] == [False, True]:
            raise ValidationError({"choice_c": "Fill in choice C before choice D."})
        if self.answer and not filled[self.LETTERS.index(self.answer)]:
            raise ValidationError({"answer": "The answer must be one of the choices."})

    def choices(self) -> list[tuple[str, str]]:
        """The (letter, text) pairs of the filled in choices."""
        return [
            (letter, text)
            for letter in self.LETTERS
            if (text := getattr(self, f"choice_{letter}"))
        ]


class Player(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="players",
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return self.name


class Answer(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    choice = models.CharField(max_length=1)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "question"],
                name="%(app_label)s_%(class)s_unique_answer",
            ),
        ]

    def __str__(self):
        return self.choice.upper()
