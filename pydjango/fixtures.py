# -*- coding: utf-8 -*-

import sys
import os
import types
from functools import partial
import pytest

from django.conf import settings
from django.db import models
from django.test.client import Client, RequestFactory
from django.utils.importlib import import_module
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import login
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
    get_user_model = lambda: User

try:
    from selenium import webdriver
    selenium_available = True
except ImportError:
    selenium_available = False

from .live_server_helper import LiveServer


def webdriver_get(self, url, prefix=''):
    url = prefix + url
    return self.__class__.get(self, url)


def django_app(name):
    def wrapper(self):
        if name not in sys.modules:
            import_module(name)
        res = sys.modules[name]
        return res
    return wrapper


def django_model(model):
    def wrapper(self):
        return model
    return wrapper


class DjangoAppsMeta(type):
    def __new__(cls, clsname, bases, dct):
        klass = type.__new__(cls, clsname, bases, dct)
        for app_name in set(settings.INSTALLED_APPS):
            name = app_name.split('.')[-1]
            setattr(klass, name, pytest.fixture(scope='session')(django_app(app_name)))

        for model in models.get_models():
            name = model._meta.object_name
            setattr(klass, name, pytest.fixture(scope='session')(django_model(model)))
        return klass

DjangoApps = DjangoAppsMeta('DjangoApps', (object, ), {})


class Fixtures(DjangoApps):

    @pytest.fixture()
    def client(self):
        """A Django test client instance"""
        return Client()

    @pytest.fixture()
    def rf(self):
        """RequestFactory instance"""
        rf = RequestFactory()
        rf.META = {}
        return rf

    @pytest.fixture
    def anon_user(self):
        """ AnonymousUser instance"""
        return AnonymousUser()

    @pytest.fixture()
    def test_user(self):
        """User instance"""
        cls = get_user_model()
        try:
            user = cls.objects.get(username='test')
        except cls.DoesNotExist:
            user = cls.objects.create_user(
                username='test',
                email='test@example.com',
                password='test')
        return user

    @pytest.fixture()
    def admin_user(self):
        cls = get_user_model()
        try:
            admin = cls.objects.get(username='admin')
        except cls.DoesNotExist:
            admin = cls.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin')
        return admin

    @pytest.fixture(scope='session')
    def settings(self):
        return settings

    @pytest.fixture()
    def uclient(self, client, test_user, rf):
        """Client instance with logged in user
        """
        test_user.backend = 'django.contrib.auth.backends.ModelBackend'
        if client.session:
            rf.session = client.session
        else:
            engine = import_module(settings.SESSION_ENGINE)
            rf.session = engine.SessionStore()
        login(rf, test_user)

        # Save the session values.
        rf.session.save()

        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        client.cookies[session_cookie] = rf.session.session_key
        cookie_data = {
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        }
        client.cookies[session_cookie].update(cookie_data)
        client.user = test_user
        return client

    @pytest.fixture()
    def aclient(self, client, admin_user, rf):
        """Client instance with logged in admin
        """
        return self.uclient(client, admin_user, rf)

    @pytest.fixture(scope='session')
    def live_server(self, request):
        server = LiveServer(self.live_server_class, os.environ.get(
            'DJANGO_LIVE_TEST_SERVER_ADDRESS', 'localhost:8081'))
        request.addfinalizer(server.stop)
        return server

    @pytest.fixture
    def driver(self, request, live_server):
        if not selenium_available:
            pytest.skip('Selenium is not installed')
        request.applymarker(pytest.mark.slow)
        request.applymarker(pytest.mark.selenium)
        driver = webdriver.Firefox()
        driver.get = types.MethodType(partial(webdriver_get, prefix=live_server.url), driver)
        request.addfinalizer(driver.quit)
        return driver
