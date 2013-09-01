# -*- coding: utf-8 -*-

import sys
import pytest

from django.conf import settings
from django.test.client import Client, RequestFactory
from django.utils.importlib import import_module
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import login
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User


def _get_django_app(name):
    if name not in sys.modules:
        import_module(name)
    return sys.modules[name]


class DjangoAppsMeta(type):
    def __new__(cls, clsname, bases, dct):
        klass = type.__new__(cls, clsname, bases, dct)
        for app_name in set(settings.INSTALLED_APPS):
            name = app_name.split('.')[-1]
            setattr(klass, name, pytest.fixture(scope='session')(
                lambda self: _get_django_app(app_name)
            ))
        return klass


class Fixtures(object):

    __metaclass__ = DjangoAppsMeta

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
        try:
            user = User.objects.get(username='test')
        except User.DoesNotExist:
            user = User.objects.create_user(
                username='test',
                email='test@example.com',
                password='test')
        return user

    @pytest.fixture()
    def admin_user(self):
        try:
            admin = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin = User.objects.create_superuser(
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
