"""
The state of a live quiz, worked out from its step, questions, and answers.

A quiz with N questions steps through:

* 0: the lobby, where players join.
* 1 to N: each question, open for answers.
* N + 1 to 2N: each answer revealed, in the same order.
* 2N + 1 onwards: the players who reached each score, from the top down.
"""

from collections import Counter
from dataclasses import dataclass
from functools import cached_property

from djangolondon.models import Answer, Player, Question, Quiz

LOBBY = "lobby"
QUESTION = "question"
REVEAL = "reveal"
RESULTS = "results"

# How many names to show in the lead or behind before summarizing the rest.
MAX_NAMES = 8


@dataclass
class Tier:
    score: int
    players: list[Player]


@dataclass
class NameGroup:
    """A group of player names, cut short so they fit on the screen."""

    score: int
    names: list[str]
    more: int


def _name_group(score: int, players: list[Player]) -> NameGroup:
    return NameGroup(
        score=score,
        names=[p.name for p in players[:MAX_NAMES]],
        more=max(len(players) - MAX_NAMES, 0),
    )


class LiveQuiz:
    def __init__(
        self,
        quiz: Quiz,
        questions: list[Question],
        players: list[Player],
        answers: list[Answer],
    ):
        self.quiz = quiz
        self.questions = questions
        self.players = players
        # player id -> question id -> choice
        self.choices: dict[int, dict[int, str]] = {p.pk: {} for p in players}
        for answer in answers:
            self.choices[answer.player_id][answer.question_id] = answer.choice

    @classmethod
    def load(cls, quiz: Quiz) -> LiveQuiz:
        """Load everything, for the screen. Three queries."""
        return cls(
            quiz,
            list(quiz.questions.all()),
            list(quiz.players.all()),
            list(
                Answer.objects.filter(player__quiz=quiz).only(
                    "player", "question", "choice"
                )
            ),
        )

    @classmethod
    def load_for_player(cls, quiz: Quiz, player: Player | None) -> LiveQuiz:
        """Load only what one player’s phone needs. Every phone polls this."""
        if player is None:
            return cls(quiz, list(quiz.questions.all()), [], [])
        return cls(
            quiz,
            list(quiz.questions.all()),
            [player],
            list(player.answers.only("player", "question", "choice")),
        )

    @property
    def step(self) -> int:
        return self.quiz.step

    @property
    def question_count(self) -> int:
        return len(self.questions)

    @property
    def phase(self) -> str:
        if self.step == 0:
            return LOBBY
        if self.step <= self.question_count:
            return QUESTION
        if self.step <= 2 * self.question_count:
            return REVEAL
        return RESULTS

    @property
    def number(self) -> int | None:
        """The 1-based number of the current question, or answer."""
        if self.phase == QUESTION:
            return self.step
        if self.phase == REVEAL:
            return self.step - self.question_count
        return None

    @property
    def question(self) -> Question | None:
        if self.number is None:
            return None
        return self.questions[self.number - 1]

    @property
    def can_join(self) -> bool:
        return self.phase in (LOBBY, QUESTION)

    def choice(self, player: Player) -> str | None:
        """The player’s choice for the current question."""
        if self.question is None:
            return None
        return self.choices[player.pk].get(self.question.pk)

    def score(self, player: Player, through: int | None = None) -> int:
        """How many of the first `through` questions the player got right."""
        choices = self.choices[player.pk]
        return sum(
            1
            for question in self.questions[:through]
            if choices.get(question.pk) == question.answer
        )

    # The screen, while questions are open

    @property
    def answered_count(self) -> int:
        return sum(1 for p in self.players if self.choice(p) is not None)

    @cached_property
    def _standings(self) -> tuple[NameGroup | None, NameGroup | None]:
        """
        Who is in the lead and who is behind, on the questions closed so far.

        Nobody sees the answers until the end, so this only gives away that
        someone is doing well, not what they answered.
        """
        if self.phase != QUESTION:
            return None, None
        closed = self.number - 1
        scores = {p.pk: self.score(p, through=closed) for p in self.players}
        if len(set(scores.values())) < 2:
            # Everyone is level, so nobody leads.
            return None, None
        top, bottom = max(scores.values()), min(scores.values())
        return (
            _name_group(top, [p for p in self.players if scores[p.pk] == top]),
            _name_group(bottom, [p for p in self.players if scores[p.pk] == bottom]),
        )

    @property
    def leaders(self) -> NameGroup | None:
        return self._standings[0]

    @property
    def trailers(self) -> NameGroup | None:
        return self._standings[1]

    # The screen, while answers are revealed

    def choice_counts(self) -> list[tuple[str, str, int]]:
        """(letter, text, how many players chose it) for the current question."""
        counts = Counter(self.choice(p) for p in self.players)
        return [
            (letter, text, counts[letter]) for letter, text in self.question.choices()
        ]

    # Results

    @cached_property
    def tiers(self) -> list[Tier]:
        """Players grouped by their final score, best first."""
        by_score: dict[int, list[Player]] = {}
        for player in self.players:
            by_score.setdefault(self.score(player), []).append(player)
        return [
            Tier(score, by_score[score]) for score in sorted(by_score, reverse=True)
        ]

    @property
    def tier_index(self) -> int | None:
        if self.phase != RESULTS:
            return None
        return self.step - 2 * self.question_count - 1

    @property
    def last_step(self) -> int:
        # With nobody playing there are no tiers, but still a results step to
        # say so.
        return 2 * self.question_count + max(len(self.tiers), 1)

    @property
    def can_go_back(self) -> bool:
        return self.step > 0

    @property
    def next_label(self) -> str | None:
        """What the quizmaster’s next button does, or None at the very end."""
        n = self.question_count
        if self.step >= self.last_step:
            return None
        if self.phase == LOBBY:
            return "Start the quiz"
        if self.phase == QUESTION:
            return "Next question" if self.number < n else "Reveal the answers"
        if self.phase == REVEAL:
            return "Next answer" if self.number < n else "Show the results"
        return f"Show {self.tiers[self.tier_index + 1].score}/{n}"

    @property
    def current_tier(self) -> Tier | None:
        if self.tier_index is None or self.tier_index >= len(self.tiers):
            return None
        return self.tiers[self.tier_index]

    @property
    def higher_tiers(self) -> list[Tier]:
        """The tiers already shown, above the current one."""
        if self.tier_index is None:
            return []
        return self.tiers[: self.tier_index]
