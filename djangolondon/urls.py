import datetime as dt

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
    path("", views.index),
    path("code-of-conduct/", views.code_of_conduct),
    path("meetups/", views.meetup_list),
    path("meetups/<isodate:date>/", views.meetup_detail),
    path("meetup/<isodate:date>/", views.meetup_redirect),
    path("favicon.ico", views.favicon),
    path("__reload__/", include("django_browser_reload.urls")),
]
