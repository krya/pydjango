# -*- coding: utf-8 -*-


def test_client(client):
    assert client


def test_rf(rf):
    assert rf


def test_user(admin_user):
    assert admin_user.pk


def test_admin_user(admin_user):
    assert admin_user.pk


def test_uclient(uclient, settings):
    assert uclient.user
    assert uclient.cookies[settings.SESSION_COOKIE_NAME]


def test_aclient(aclient):
    from django.core.urlresolvers import reverse
    response = aclient.get(reverse('admin:index'))
    assert response.status_code == 200


def test_installed_app(auth):
    assert hasattr(auth, 'models')
    assert hasattr(auth.models, 'User')
