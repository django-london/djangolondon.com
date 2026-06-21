from django.db import migrations, models


def clear_speakers_and_talks(apps, schema_editor):
    apps.get_model("djangolondon", "Talk").objects.all().delete()
    apps.get_model("djangolondon", "Speaker").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("djangolondon", "0003_talk_djangolondon_talk_unique_talk"),
    ]

    operations = [
        migrations.RunPython(clear_speakers_and_talks, migrations.RunPython.noop),
        migrations.AddField(
            model_name="speaker",
            name="slug",
            field=models.SlugField(default="", unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="speaker",
            name="github_username",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="speaker",
            name="mastodon_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="speaker",
            name="bluesky_handle",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="speaker",
            name="name",
            field=models.CharField(max_length=200),
        ),
        migrations.RemoveConstraint(
            model_name="talk",
            name="djangolondon_talk_unique_talk",
        ),
        migrations.RemoveField(
            model_name="talk",
            name="speaker",
        ),
        migrations.AddField(
            model_name="talk",
            name="speakers",
            field=models.ManyToManyField(to="djangolondon.speaker"),
        ),
        migrations.AddConstraint(
            model_name="talk",
            constraint=models.UniqueConstraint(
                fields=("meetup", "title"), name="djangolondon_talk_unique_talk"
            ),
        ),
    ]
