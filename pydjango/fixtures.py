# -*- coding: utf-8 -*-

import pytest

from django.conf import settings
from django.contrib.auth.models import User
from django.test.client import Client
from django.contrib.auth import login
from django.utils.importlib import import_module

from .client import RequestFactory

class Fixtures(object):

    @pytest.fixture()
    def client(self):
        """A Django test client instance"""
        return Client()

    @pytest.fixture()
    def rf(self):
        """RequestFactory instance"""
        return RequestFactory()

    @pytest.fixture()
    def user(self):
        """User instance"""
        try:
            user = User.objects.get(username='test')
        except User.DoesNotExist:
            user = User.objects.create_user('test', 'test@example.com')
        return user


    @pytest.fixture()
    def admin(self):
        try:
            admin = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin = User.objects.create_superuser('admin', 'admin@example.com',
                                                  'admin')
        return admin

    @pytest.fixture(scope='session')
    def settings(self):
        return settings

    @pytest.fixture()
    def uclient(self, client, user, rf):
        """Client instance with logged in user
        """
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        if client.session:
            rf.session = client.session
        else:
            engine = import_module(settings.SESSION_ENGINE)
            rf.session = engine.SessionStore()
        login(rf, user)

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
        client.user = user
        # client.login(username=user.username, password=user.password)
        return client

    @pytest.fixture()
    def aclient(self, client, admin, rf):
        """Client instance with logged in admin
        """
        return self.uclient(client, admin, rf)