from django.contrib import admin

from djangolondon.models import Meetup, Speaker, Talk


class SpeakerTalkInline(admin.TabularInline):
    model = Talk
    extra = 0
    readonly_fields = ["title", "meetup"]
    fields = ["title", "meetup"]


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    readonly_fields = ["name"]
    inlines = [SpeakerTalkInline]


class TalkInline(admin.TabularInline):
    model = Talk
    extra = 0
    readonly_fields = ["title", "speaker", "meetup"]


@admin.register(Meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = ["title", "date"]
    inlines = [TalkInline]
    readonly_fields = ["title", "date", "meetup_url", "skills_matter_url"]


@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    list_display = ["title", "speaker", "meetup"]
    search_fields = ["title", "speaker__name"]
    list_select_related = ["speaker", "meetup"]
    readonly_fields = [
        "meetup",
        "speaker",
        "title",
        "description",
        "blogpost_url",
        "slides_url",
        "skills_matter_url",
    ]
