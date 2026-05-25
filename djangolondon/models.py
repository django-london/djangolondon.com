from django.db import models


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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["meetup", "speaker", "title"],
                name="%(app_label)s_%(class)s_unique_talk",
            ),
        ]

    def __str__(self):
        return self.title
