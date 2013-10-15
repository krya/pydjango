# -*- coding: utf-8 -*-

import pytest

from django.contrib.auth.models import User
from django.test.testcases import TestCase, TransactionTestCase
from pydjango.patches import Function, Class, Instance

def test_no_savepoints(request):
    "no fixtures and no setup_module so shouldnt have savepoints"
    for node in request.node.listchain():
        assert not getattr(node, 'savepoints', {})


def test_function_has_savepoints(request):
    assert User.objects.count() == 0
    assert request.node.savepoints
    for node in request.node.listchain():
        if node != request.node:
            assert not getattr(node, 'savepoints', {})


class TestClassLazySavepoint(object):

    @classmethod
    def setup_class(cls):
        assert User.objects.count() == 0
        User.objects.create(username='test', password='pass')

    def setup_method(self, method):
        assert User.objects.count() == 1
        User.objects.create(username='test2', password='pass')

    def test_lazy_method(self, request):
        assert User.objects.count() == 2
        assert request.node.savepoints
        for node in request.node.listchain():
            if isinstance(node, (Function, Class, Instance)):
                assert node.savepoints


@pytest.fixture(scope='class')
def classrequest(request):
    request.cls.request = request

@pytest.mark.usefixtures("classrequest")
class TestCaceLazySavepoint(TestCase):

    def test_lazy_method(self):
        # touch database
        User.objects.create(username='test2', password='pass')
        assert self.request.node.savepoints
        for node in self.request.node.listchain():
            if isinstance(node, (Function, Class, Instance)):
                assert node.savepoints

@pytest.mark.usefixtures("classrequest")
class TestTransactionSavepoints(TransactionTestCase):
    def test_lazy_savepoints(self):
        User.objects.create(username='test2', password='pass')
        for node in self.request.node.listchain():
            assert not getattr(node, 'savepoints', {}), node.cls
