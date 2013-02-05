"""A py.test plugin which helps testing Django applications

This plugin handles creating and destroying the test environment and
test database and provides some useful text fixtues.
"""

import os
import pytest


try:
    from django.conf import ENVIRONMENT_VARIABLE, settings
    DJANGO_INSTALLED = True
except ImportError:
    DJANGO_INSTALLED = False
    ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"




def pytest_addoption(parser):
    group = parser.getgroup('pydjango')
    group._addoption('--django-settings',
                     action='store', type='string', dest='ds', default=None,
                     help='Set %s.' %ENVIRONMENT_VARIABLE)
    parser.addini(ENVIRONMENT_VARIABLE,
                  'Django settings module to use by pydjango.')

@pytest.mark.tryfirst
def pytest_configure(config, __multicall__):
    if not DJANGO_INSTALLED:
        return
    settings_module = config.option.ds or config.getini(ENVIRONMENT_VARIABLE) or\
                      os.environ.get(ENVIRONMENT_VARIABLE)
    if settings_module:
        os.environ[ENVIRONMENT_VARIABLE] = settings_module
    else:
        if not settings.configured:
            __multicall__.execute()
    try:
        from .django_plugin import DjangoPlugin
        config.pluginmanager.register(DjangoPlugin(config), '_pydjango')
    except ImportError, e:
        raise pytest.UsageError('Failed to import project settings. (%s)' %str(e))

