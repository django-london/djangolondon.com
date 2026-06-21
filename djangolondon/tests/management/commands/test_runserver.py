from django.test import SimpleTestCase

from djangolondon.management.commands.runserver import Command


class RunserverTests(SimpleTestCase):
    def test_default_port(self):
        command = Command()
        self.assertEqual(command.default_port, "8123")
