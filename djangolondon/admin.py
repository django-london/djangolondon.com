from django.contrib import admin
from django.utils.html import format_html

from djangolondon.models import Entry, Meetup, Prize, PrizeDraw, Speaker, Talk


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


class PrizeInline(admin.TabularInline):
    model = Prize
    extra = 1
    fields = ["order", "name", "description", "voucher", "winner", "drawn_at"]
    readonly_fields = ["winner", "drawn_at"]


class EntryInline(admin.TabularInline):
    model = Entry
    extra = 0
    fields = ["name", "email", "created_at"]
    readonly_fields = ["name", "email", "created_at"]

    def has_add_permission(self, request, obj):
        return False


@admin.register(PrizeDraw)
class PrizeDrawAdmin(admin.ModelAdmin):
    list_display = ["name", "meetup", "entries_open", "screen_link"]
    list_select_related = ["meetup"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [PrizeInline, EntryInline]

    @admin.display(description="screen")
    def screen_link(self, obj):
        return format_html(
            '<a href="/prize-draws/{}/screen/">Run draw</a>',
            obj.slug,
        )


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
