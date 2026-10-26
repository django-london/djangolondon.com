from django import forms
from django.contrib import admin
from django.utils.html import format_html

from djangolondon.forms import PrizeForm
from djangolondon.models import (
    Entry,
    Meetup,
    Player,
    Prize,
    PrizeDraw,
    Question,
    Quiz,
    Speaker,
    Talk,
)


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
    form = PrizeForm
    # Several blank rows, since adding more needs the admin's JavaScript.
    extra = 3
    fields = [
        "order",
        "name",
        "description",
        "voucher_upload",
        "voucher_filename",
        "winner",
        "drawn_at",
    ]
    readonly_fields = ["voucher_filename", "winner", "drawn_at"]


class EntryInline(admin.TabularInline):
    model = Entry
    extra = 0
    fields = ["name", "created_at"]
    readonly_fields = ["name", "created_at"]

    def has_add_permission(self, request, obj):
        return False


@admin.register(PrizeDraw)
class PrizeDrawAdmin(admin.ModelAdmin):
    list_display = ["name", "entries_open", "screen_link"]
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


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 3
    fields = [
        "order",
        "text",
        ("choice_a", "choice_b"),
        ("choice_c", "choice_d"),
        "answer",
        "explanation",
    ]

    def get_formset(self, request, obj=None, **kwargs):
        # Questions are a line or two, not an essay.
        kwargs["widgets"] = {
            "text": forms.Textarea(attrs={"rows": 2, "cols": 80}),
            "explanation": forms.Textarea(attrs={"rows": 4, "cols": 80}),
        }
        return super().get_formset(request, obj, **kwargs)

    # Imported quizzes are edited in their data files instead.

    def has_add_permission(self, request, obj):
        return obj is None or not obj.imported

    def has_change_permission(self, request, obj=None):
        return obj is None or not obj.imported

    def has_delete_permission(self, request, obj=None):
        return obj is None or not obj.imported


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0
    fields = ["name", "created_at"]
    readonly_fields = ["name", "created_at"]

    def has_add_permission(self, request, obj):
        return False


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["title", "date", "published", "screen_link", "play_link"]
    list_filter = ["published"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [QuestionInline, PlayerInline]

    def get_fields(self, request, obj=None):
        fields = ["slug", "title", "date", "description", "published"]
        if obj is not None and obj.imported:
            fields.insert(0, "data_file")
        return fields

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.imported:
            return ["data_file", "slug", "title", "date", "description"]
        return []

    def get_prepopulated_fields(self, request, obj=None):
        if obj is not None and obj.imported:
            return {}
        return self.prepopulated_fields

    @admin.display(description="data file")
    def data_file(self, obj):
        return format_html(
            "Edit <code>data/quizzes/{}.toml</code> to change this quiz.",
            obj.slug,
        )

    @admin.display(description="live")
    def screen_link(self, obj):
        return format_html('<a href="/quizzes/{}/screen/">Run live</a>', obj.slug)

    @admin.display(description="play")
    def play_link(self, obj):
        return format_html('<a href="/quizzes/{}/">Play alone</a>', obj.slug)
