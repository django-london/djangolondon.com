from django.urls import include, path

from djangolondon import views

urlpatterns = [
    path("", views.index),
    path("code-of-conduct/", views.code_of_conduct),
    path("favicon.ico", views.favicon),
    path("__reload__/", include("django_browser_reload.urls")),
]
