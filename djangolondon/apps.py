from django.apps import AppConfig


class DjangoLondonConfig(AppConfig):
    name = "djangolondon"

    def ready(self):
        import djangolondon.receivers  # noqa: F401
