# -*- coding: utf-8 -*-

import pytest

def setup_module():
    from django.contrib.auth.models import User
    User.objects.create(username='username', email='test@example.com')

@pytest.mark.parametrize('attempt', range(2))
def test_module_setup(attempt):
    from django.contrib.auth.models import User
    assert User.objects.count() == 1


# this one crashes python but only with sqlite
# from django.core.urlresolvers import reverse
# @pytest.mark.parametrize('longattr', range(160))
# def test_admin(aclient, longattr):
#     resp = aclient.get(reverse('admin:index'))
#     assert resp.status_code == 200
