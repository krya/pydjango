# -*- coding: utf-8 -*-


def test_client(client):
    assert client


def test_rf(rf):
    assert rf


def test_user(user):
    assert user.pk


def test_admin(admin):
    assert admin.pk


def test_uclient(uclient, settings):
    assert uclient.user
    assert uclient.cookies[settings.SESSION_COOKIE_NAME]


def test_aclient(aclient):
    from django.core.urlresolvers import reverse
    response = aclient.get(reverse('admin:index'))
    assert response.status_code == 200
