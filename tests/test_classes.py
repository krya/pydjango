# -*- coding: utf-8 -*-

import pytest

from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase

def setup_module():
    User.objects.create(username='username', email='test@example.com')


class TestPyClass(object):

    def setup_class(self):
        User.objects.create(username='setup_class', email='class@example.com')

    def setup_method(self, method):
        User.objects.create(username='setup_method', email='method@example.com')

    @pytest.mark.parametrize('attempt', range(2))
    def test_method(self, attempt):
        assert User.objects.count() == 3


class TestTestCase(TestCase):

    def test_case_method(self):
        # should have user from setup_module
        assert User.objects.count() == 1

    def test_case_second_method(self):
        assert User.objects.count() == 1


class TestTransaction(TransactionTestCase):

    def test_trans_method(self):
        assert User.objects.count() == 0
