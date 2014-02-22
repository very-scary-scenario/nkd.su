from django.test import TestCase

from test_everything.mixins import EverythingMixin


class TestEverything(EverythingMixin, TestCase):
    pass
