import re
import tomllib
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from djangolondon.models import Meetup, Question, Quiz, Speaker, Talk

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "meetups"
SPEAKERS_DIR = BASE_DIR / "data" / "speakers"
QUIZZES_DIR = BASE_DIR / "data" / "quizzes"


def _dev_credentials():
    readme = (BASE_DIR / "README.md").read_text()
    username_match = re.search(r"^username: (.+)$", readme, re.MULTILINE)
    password_match = re.search(r"^password: (.+)$", readme, re.MULTILINE)
    assert username_match and password_match, "Dev credentials not found in README.md"
    return username_match[1], password_match[1]


@receiver(post_migrate)
def create_dev_superuser(sender, **kwargs):
    if sender.name != "djangolondon" or not settings.DEBUG:
        return

    username, password = _dev_credentials()
    user, created = User.objects.get_or_create(
        username=username, defaults={"is_staff": True, "is_superuser": True}
    )
    if created:
        user.set_password(password)
        user.save()


@receiver(post_migrate)
def load_static_data(sender, **kwargs):
    if sender.name != "djangolondon":
        return

    for toml_file in sorted(SPEAKERS_DIR.glob("*.toml")):
        slug = toml_file.stem
        with toml_file.open("rb") as f:
            data = tomllib.load(f)

        Speaker.objects.update_or_create(
            slug=slug,
            defaults={
                "name": data["name"],
                "github_username": data.get("github_username", ""),
                "mastodon_url": data.get("mastodon_url", ""),
                "bluesky_handle": data.get("bluesky_handle", ""),
            },
        )

    for toml_file in sorted(DATA_DIR.glob("*.toml")):
        with toml_file.open("rb") as f:
            data = tomllib.load(f)

        meetup, _ = Meetup.objects.update_or_create(
            date=data["date"],
            defaults={
                "title": data["title"],
                "meetup_url": data.get("meetup_url", ""),
                "skills_matter_url": data.get("skills_matter_url", ""),
            },
        )

        for talk_data in data.get("talks", []):
            talk, _ = Talk.objects.update_or_create(
                meetup=meetup,
                title=talk_data["title"],
                defaults={
                    "description": talk_data.get("description", "").strip(),
                    "blogpost_url": talk_data.get("blogpost_url", ""),
                    "slides_url": talk_data.get("slides_url", ""),
                    "skills_matter_url": talk_data.get("skills_matter_url", ""),
                },
            )
            speakers = Speaker.objects.filter(slug__in=talk_data["speakers"])
            missing = set(talk_data["speakers"]) - set(
                speakers.values_list("slug", flat=True)
            )
            if missing:
                raise ValueError(f"Unknown speaker slugs: {missing}")
            talk.speakers.set(speakers)

    for toml_file in sorted(QUIZZES_DIR.glob("*.toml")):
        with toml_file.open("rb") as f:
            data = tomllib.load(f)
        load_quiz(toml_file.stem, data)


def load_quiz(slug: str, data: dict) -> Quiz:
    """
    Create or refresh a quiz from its data file.

    Questions are matched up by position and updated in place, so that a live
    quiz’s answers survive a typo fix.
    """
    fields = {
        "title": data["title"],
        "date": data["date"],
        "description": data.get("description", "").strip(),
        "imported": True,
    }
    quiz, _ = Quiz.objects.update_or_create(
        slug=slug,
        defaults=fields,
        # Imported quizzes have already been played, so are listed from the
        # start. After that, the admin decides.
        create_defaults={**fields, "published": True},
    )

    for order, question_data in enumerate(data["questions"], start=1):
        choices = question_data["choices"]
        if not 2 <= len(choices) <= len(Question.LETTERS):
            raise ValueError(f"{slug} question {order}: needs two to four choices")
        if question_data["answer"] not in Question.LETTERS[: len(choices)]:
            raise ValueError(f"{slug} question {order}: answer is not a choice")
        padded = choices + [""] * (len(Question.LETTERS) - len(choices))
        Question.objects.update_or_create(
            quiz=quiz,
            order=order,
            defaults={
                "text": question_data["text"],
                **{
                    f"choice_{letter}": text
                    for letter, text in zip(Question.LETTERS, padded, strict=True)
                },
                "answer": question_data["answer"],
                "explanation": question_data.get("explanation", "").strip(),
            },
        )
    quiz.questions.filter(order__gt=len(data["questions"])).delete()
    return quiz
