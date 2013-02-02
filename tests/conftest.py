# -*- coding: utf-8 -*-

SETTINGS = {
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    'SITE_ID':1,
    'SECRET_KEY' : '*_1cc9n+lc@l$#hmd-)#(@0-i=@jbzb2zkmbv8nvf)qodq37^l',
    'ROOT_URLCONF' : 'tests.urls',
    'INSTALLED_APPS' : (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
    )
}



def pytest_configure():
    from django.conf import settings
    if not settings.configured:
        settings.configure(**SETTINGS)
