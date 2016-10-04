"""A py.test plugin which helps testing Django applications

This plugin handles creating and destroying the test environment and
test database and provides some useful text fixtues.
"""

import os
import pytest


try:
    import django
    from django.conf import ENVIRONMENT_VARIABLE, settings
    DJANGO_INSTALLED = True
except ImportError:
    DJANGO_INSTALLED = False
    ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"


DEFAULT_LIVE_SERVER = 'django.test.testcases.StoppableWSGIServer'


def pytest_addoption(parser):
    group = parser.getgroup('pydjango')
    group._addoption('--django-settings',
                     action='store', type='string', dest='ds', default=None,
                     help='Set %s.' % ENVIRONMENT_VARIABLE)
    group._addoption('--create-db',
                     action='store_true', dest='create_db', default=False,
                     help='Force database creation')
    group._addoption('--migrate',
                     action='store_true', dest='migrate', default=False,
                     help='sync db and run migrations')
    group._addoption('--liveserver-class',
                     action='store', type='string', dest='liveserver_class', default=DEFAULT_LIVE_SERVER,
                     help='Set live server class to serve requests. default: %s' % DEFAULT_LIVE_SERVER)
    group._addoption('--skip-trans',
                     action='store_true', dest='skip_trans', default=False,
                     help='Skip transactional tests')
    parser.addini(ENVIRONMENT_VARIABLE,
                  'Django settings module to use by pydjango.')


@pytest.mark.tryfirst
def pytest_configure(config, __multicall__):
    if not DJANGO_INSTALLED:
        return
    settings_module = config.option.ds or \
        config.getini(ENVIRONMENT_VARIABLE) or \
        os.environ.get(ENVIRONMENT_VARIABLE)
    if settings_module:
        os.environ[ENVIRONMENT_VARIABLE] = settings_module
    else:
        if not settings.configured:
            __multicall__.execute()
    if hasattr(django, 'setup'):
        django.setup()
    try:
        from .django_plugin import DjangoPlugin
        manager = config.pluginmanager
        plugin = DjangoPlugin(config)
        manager.register(plugin, '_pydjango')
        # insert new upload right after main plugin so conftest could override fixtures
        main_index = manager._plugins.index(manager.getplugin('pydjango'))
        manager._plugins.pop(manager._plugins.index(plugin))
        manager._plugins.insert(main_index + 1, plugin)
    except ImportError as e:
        raise pytest.UsageError('Failed to import project settings. (%s)' % str(e))
