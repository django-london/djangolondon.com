from django.urls import include, path

from djangolondon import views

urlpatterns = [
    path("", views.index),
    path("favicon.ico", views.favicon),
    path("__reload__/", include("django_browser_reload.urls")),
]
