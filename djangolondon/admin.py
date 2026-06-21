from django.contrib import admin

from djangolondon.models import Meetup, Speaker, Talk


class SpeakerTalkInline(admin.TabularInline):
    model = Talk.speakers.through
    extra = 0
    verbose_name = "talk"
    verbose_name_plural = "talks"
    readonly_fields = ["talk", "speaker"]


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    search_fields = ["name", "slug"]
    readonly_fields = ["slug", "name"]
    fields = ["slug", "name", "github_username", "mastodon_url", "bluesky_handle"]
    inlines = [SpeakerTalkInline]


class TalkInline(admin.TabularInline):
    model = Talk
    extra = 0
    readonly_fields = ["title", "speakers_display", "meetup"]
    fields = ["title", "speakers_display", "meetup"]

    @admin.display(description="speakers")
    def speakers_display(self, obj):
        return ", ".join(s.name for s in obj.speakers.all())


@admin.register(Meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = ["title", "date"]
    inlines = [TalkInline]
    readonly_fields = ["title", "date", "meetup_url", "skills_matter_url"]


@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    list_display = ["title", "speakers_display", "meetup"]
    search_fields = ["title", "speakers__name"]
    list_select_related = ["meetup"]
    readonly_fields = [
        "meetup",
        "speakers",
        "title",
        "description",
        "blogpost_url",
        "slides_url",
        "skills_matter_url",
    ]

    @admin.display(description="speakers")
    def speakers_display(self, obj):
        return ", ".join(s.name for s in obj.speakers.all())
