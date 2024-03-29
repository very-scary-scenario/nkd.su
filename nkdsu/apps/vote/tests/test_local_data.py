import subprocess
from unittest import TestCase

from django.core.management import call_command


class LocalDataTest(TestCase):
    def test_local_data_udated(self) -> None:
        def status() -> str:
            return subprocess.check_output(['git', 'status', '-s']).decode('utf-8')

        initial_status = status()

        call_command('update_local_data')

        self.assertEqual(initial_status, status())
