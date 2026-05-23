import tomllib
from pathlib import Path

from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "meetups"


class Speaker(models.Model):
    name = models.CharField(max_length=200, unique=True)

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
    speaker = models.ForeignKey(Speaker, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    blogpost_url = models.URLField(blank=True)
    slides_url = models.URLField(blank=True)
    skills_matter_url = models.URLField(blank=True)

    def __str__(self):
        return self.title


@receiver(post_migrate)
def load_static_data(sender, **kwargs):
    if sender.name != "djangolondon":
        return

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
            speaker_data = talk_data["speaker"]
            speaker, _ = Speaker.objects.get_or_create(name=speaker_data["name"])

            Talk.objects.update_or_create(
                meetup=meetup,
                speaker=speaker,
                title=talk_data["title"],
                defaults={
                    "description": talk_data.get("description", "").strip(),
                    "blogpost_url": talk_data.get("blogpost_url", ""),
                    "slides_url": talk_data.get("slides_url", ""),
                    "skills_matter_url": talk_data.get("skills_matter_url", ""),
                },
            )
