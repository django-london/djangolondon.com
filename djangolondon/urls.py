import datetime as dt

from django.contrib import admin
from django.urls import include, path, register_converter

from djangolondon import views


class ISODateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"

    def to_python(self, value):
        return dt.date.fromisoformat(value)

    def to_url(self, value):
        return value.isoformat()


register_converter(ISODateConverter, "isodate")

urlpatterns = [
    # Static pages
    path("", views.index),
    path("code-of-conduct/", views.code_of_conduct),
    # Meetups and related data
    path("meetup/<isodate:date>/", views.meetup_redirect),
    path(
        "meetups/",
        include(
            [
                path("", views.meetup_list),
                path("<isodate:date>/", views.meetup_detail),
            ]
        ),
    ),
    path(
        "speakers/",
        include(
            [
                path("", views.speaker_list),
                path("<slug:slug>/", views.speaker_detail),
            ]
        ),
    ),
    path("slides/<str:date>/<str:filename>", views.meetup_slides),
    # Prize draws
    path(
        "prize-draws/<slug:slug>/",
        include(
            [
                path("", views.prize_draw_join),
                path("enter/", views.prize_draw_enter),
                path("status/", views.prize_draw_status),
                path(
                    "screen/",
                    include(
                        [
                            path("", views.prize_draw_screen),
                            path("status/", views.prize_draw_screen_status),
                            path("draw/", views.prize_draw_draw),
                            path(
                                "entries/<int:pk>/remove/",
                                views.prize_draw_remove_entry,
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
    path("prizes/<int:pk>/voucher/", views.prize_voucher),
    # Quizzes
    path(
        "quizzes/",
        include(
            [
                path("", views.quiz_list),
                path(
                    "<slug:slug>/",
                    include(
                        [
                            path("", views.quiz_detail),
                            path("live/", views.quiz_live),
                            path("live/join/", views.quiz_live_join),
                            path("live/status/", views.quiz_live_status),
                            path("live/answer/", views.quiz_live_answer),
                            path(
                                "screen/",
                                include(
                                    [
                                        path("", views.quiz_screen),
                                        path("status/", views.quiz_screen_status),
                                        path("next/", views.quiz_screen_next),
                                        path("back/", views.quiz_screen_back),
                                        path("reset/", views.quiz_screen_reset),
                                        path(
                                            "players/<int:pk>/remove/",
                                            views.quiz_screen_remove_player,
                                        ),
                                    ]
                                ),
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
    # Public files and other special routes
    path("favicon.ico", views.favicon),
    path(".well-known/atproto-did", views.atproto_did),
    # Organizers
    path("organizers/", views.organizer_index),
    path("organizers/<isodate:date>/", views.organizer_slides),
    # Admin
    path("organizers-admin/", admin.site.urls),
    # django-browser-reload (development only)
    path("__reload__/", include("django_browser_reload.urls")),
]
