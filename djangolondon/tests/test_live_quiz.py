import datetime as dt

from django.test import TestCase

from djangolondon import live_quiz
from djangolondon.live_quiz import LiveQuiz
from djangolondon.models import Answer, Player, Question, Quiz


class LiveQuizTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quiz = Quiz.objects.create(
            slug="quiz-2026", title="Django Quiz 2026", date=dt.date(2026, 12, 8)
        )
        cls.q1 = Question.objects.create(
            quiz=cls.quiz,
            order=1,
            text="What is Django?",
            choice_a="A web framework",
            choice_b="A guitarist",
            choice_c="A pony",
            answer="a",
        )
        cls.q2 = Question.objects.create(
            quiz=cls.quiz,
            order=2,
            text="What is a pony?",
            choice_a="A horse",
            choice_b="A pegasus",
            answer="b",
        )
        cls.alice = Player.objects.create(quiz=cls.quiz, name="Alice")
        cls.bob = Player.objects.create(quiz=cls.quiz, name="Bob")

    def answer(self, player, question, choice):
        Answer.objects.create(player=player, question=question, choice=choice)

    def at_step(self, step):
        Quiz.objects.filter(pk=self.quiz.pk).update(step=step)
        self.quiz.refresh_from_db()
        return LiveQuiz.load(self.quiz)


class PhaseTests(LiveQuizTestCase):
    def test_lobby(self):
        live = self.at_step(0)

        assert live.phase == live_quiz.LOBBY
        assert live.number is None
        assert live.question is None
        assert live.can_join
        assert not live.can_go_back
        assert live.next_label == "Start the quiz"

    def test_first_question(self):
        live = self.at_step(1)

        assert live.phase == live_quiz.QUESTION
        assert live.number == 1
        assert live.question == self.q1
        assert live.can_join
        assert live.can_go_back
        assert live.next_label == "Next question"

    def test_last_question(self):
        live = self.at_step(2)

        assert live.question == self.q2
        assert live.next_label == "Reveal the answers"

    def test_first_reveal(self):
        live = self.at_step(3)

        assert live.phase == live_quiz.REVEAL
        assert live.number == 1
        assert live.question == self.q1
        assert not live.can_join
        assert live.next_label == "Next answer"

    def test_last_reveal(self):
        live = self.at_step(4)

        assert live.question == self.q2
        assert live.next_label == "Show the results"

    def test_results(self):
        self.answer(self.alice, self.q1, "a")

        live = self.at_step(5)

        assert live.phase == live_quiz.RESULTS
        assert live.number is None
        assert live.question is None
        assert live.tier_index == 0
        assert live.next_label == "Show 0/2"

    def test_last_results(self):
        self.answer(self.alice, self.q1, "a")

        live = self.at_step(6)

        assert live.tier_index == 1
        assert live.last_step == 6
        assert live.next_label is None


class ChoiceTests(LiveQuizTestCase):
    def test_choice(self):
        self.answer(self.alice, self.q1, "b")

        live = self.at_step(1)

        assert live.choice(self.alice) == "b"
        assert live.choice(self.bob) is None

    def test_choice_outside_a_question(self):
        self.answer(self.alice, self.q1, "b")

        live = self.at_step(0)

        assert live.choice(self.alice) is None


class ScoreTests(LiveQuizTestCase):
    def test_score(self):
        self.answer(self.alice, self.q1, "a")
        self.answer(self.alice, self.q2, "b")
        self.answer(self.bob, self.q1, "b")
        self.answer(self.bob, self.q2, "b")

        live = LiveQuiz.load(self.quiz)

        assert live.score(self.alice) == 2
        assert live.score(self.alice, through=1) == 1
        assert live.score(self.bob) == 1
        assert live.score(self.bob, through=1) == 0


class StandingsTests(LiveQuizTestCase):
    def test_answered_count(self):
        self.answer(self.alice, self.q1, "a")

        live = self.at_step(1)

        assert live.answered_count == 1

    def test_first_question_has_no_standings(self):
        live = self.at_step(1)

        assert live.leaders is None
        assert live.trailers is None

    def test_standings_count_closed_questions_only(self):
        self.answer(self.alice, self.q1, "a")
        self.answer(self.bob, self.q1, "c")
        # Bob gets the open question right, but that must not show yet.
        self.answer(self.bob, self.q2, "b")

        live = self.at_step(2)

        assert live.leaders == live_quiz.NameGroup(score=1, names=["Alice"], more=0)
        assert live.trailers == live_quiz.NameGroup(score=0, names=["Bob"], more=0)

    def test_everyone_level(self):
        self.answer(self.alice, self.q1, "a")
        self.answer(self.bob, self.q1, "a")

        live = self.at_step(2)

        assert live.leaders is None
        assert live.trailers is None

    def test_no_standings_outside_questions(self):
        self.answer(self.alice, self.q1, "a")

        live = self.at_step(3)

        assert live.leaders is None

    def test_many_names_are_cut_short(self):
        players = [
            Player.objects.create(quiz=self.quiz, name=f"Player {i}") for i in range(10)
        ]
        for player in players:
            self.answer(player, self.q1, "a")

        live = self.at_step(2)

        assert live.leaders.names == [f"Player {i}" for i in range(8)]
        assert live.leaders.more == 2
        assert live.trailers.names == ["Alice", "Bob"]


class ChoiceCountsTests(LiveQuizTestCase):
    def test_choice_counts(self):
        self.answer(self.alice, self.q1, "a")
        self.answer(self.bob, self.q1, "a")

        live = self.at_step(3)

        assert live.choice_counts() == [
            ("a", "A web framework", 2),
            ("b", "A guitarist", 0),
            ("c", "A pony", 0),
        ]


class TierTests(LiveQuizTestCase):
    def test_tiers(self):
        carol = Player.objects.create(quiz=self.quiz, name="Carol")
        self.answer(self.alice, self.q1, "a")
        self.answer(self.alice, self.q2, "b")
        self.answer(carol, self.q1, "a")

        live = self.at_step(5)

        assert live.tiers == [
            live_quiz.Tier(2, [self.alice]),
            live_quiz.Tier(1, [carol]),
            live_quiz.Tier(0, [self.bob]),
        ]
        assert live.current_tier == live_quiz.Tier(2, [self.alice])
        assert live.higher_tiers == []
        assert live.next_label == "Show 1/2"

    def test_stepping_down(self):
        self.answer(self.alice, self.q1, "a")

        live = self.at_step(6)

        assert live.current_tier == live_quiz.Tier(0, [self.bob])
        assert live.higher_tiers == [live_quiz.Tier(1, [self.alice])]

    def test_no_current_tier_outside_results(self):
        live = self.at_step(4)

        assert live.tier_index is None
        assert live.current_tier is None
        assert live.higher_tiers == []

    def test_nobody_played(self):
        Player.objects.all().delete()

        live = self.at_step(5)

        assert live.tiers == []
        assert live.current_tier is None
        # Still a results step, to say nobody played.
        assert live.last_step == 5
        assert live.next_label is None


class LoadForPlayerTests(LiveQuizTestCase):
    def test_only_loads_the_player(self):
        self.answer(self.alice, self.q1, "a")
        self.answer(self.bob, self.q1, "b")

        with self.assertNumQueries(2):
            live = LiveQuiz.load_for_player(self.quiz, self.alice)

        assert live.players == [self.alice]
        assert live.score(self.alice) == 1

    def test_without_a_player(self):
        with self.assertNumQueries(1):
            live = LiveQuiz.load_for_player(self.quiz, None)

        assert live.players == []
        assert live.question_count == 2


class EmptyQuizTests(TestCase):
    def test_no_questions(self):
        quiz = Quiz.objects.create(
            slug="empty", title="Empty", date=dt.date(2026, 1, 1)
        )

        live = LiveQuiz.load(quiz)

        assert live.phase == live_quiz.LOBBY
        assert live.question_count == 0
        assert live.last_step == 1
