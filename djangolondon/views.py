from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


def index(request):
    return render(request, "index.html")


def code_of_conduct(request):
    return render(
        request,
        "code-of-conduct.html",
        {"title": "Code of Conduct"},
    )


@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.BASE_DIR / "djangolondon/static/favicon.svg").open("rb")
    return FileResponse(file)
