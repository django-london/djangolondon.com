from django.http import HttpResponsePermanentRedirect

CANONICAL_HOST = "djangolondon.com"
WWW_HOST = f"www.{CANONICAL_HOST}"


class WWWRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.get_host().partition(":")[0] == WWW_HOST:
            return HttpResponsePermanentRedirect(
                f"{request.scheme}://{CANONICAL_HOST}{request.get_full_path()}"
            )
        return self.get_response(request)
