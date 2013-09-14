# -*- coding: utf-8 -*-

from django.contrib.auth.models import User


def test_client(client):
    assert client


def test_rf(rf):
    assert rf


def test_user(test_user):
    assert isinstance(test_user, User)
    assert test_user.pk


def test_admin_user(admin_user):
    assert isinstance(admin_user, User)
    assert admin_user.pk


def test_uclient(uclient, settings):
    assert uclient.user
    assert uclient.cookies[settings.SESSION_COOKIE_NAME]


def test_aclient(aclient):
    from django.core.urlresolvers import reverse
    response = aclient.get(reverse('admin:index'))
    assert response.status_code == 200


def test_installed_app(contenttypes):
    from django.contrib import contenttypes as nonfixture_contenttypes
    assert contenttypes is nonfixture_contenttypes


def test_models(User):
    from django.contrib.auth.models import User as NonFixtureUser
    assert User is NonFixtureUser
