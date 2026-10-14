from django.test import SimpleTestCase


class WWWRedirectMiddlewareTests(SimpleTestCase):
    def test_www_redirects_to_canonical_host(self):
        response = self.client.get(
            "/code-of-conduct/?a=b", headers={"host": "www.djangolondon.com"}
        )

        assert response.status_code == 301
        assert response["Location"] == "http://djangolondon.com/code-of-conduct/?a=b"

        response = self.client.get("/", headers={"host": "www.djangolondon.com:8080"})

        assert response.status_code == 301
        assert response["Location"] == "http://djangolondon.com/"

    def test_canonical_host_not_redirected(self):
        response = self.client.get("/missing/", headers={"host": "djangolondon.com"})

        assert response.status_code == 404
