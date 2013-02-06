# -*- coding: utf-8 -*-

from itertools import groupby, chain
import unittest

import pytest

from django.conf import settings
from django.db import connections, transaction
from django.core import management
from django.test.testcases import (TransactionTestCase, TestCase,
                                   disable_transaction_methods,
                                    restore_transaction_methods)
from django.test.simple import DjangoTestSuiteRunner


from .patches import Module, SUnitTestCase
from .db_reuse import monkey_patch_creation_for_db_reuse, wrap_database
from .fixtures import Fixtures
from .utils import nop, is_transaction_test


class  DjangoPlugin(Fixtures):

    def __init__(self, config):
        self.config = config
        self.configure()
        config.pluginmanager._setns(pytest, {'Module':Module})

    def configure(self):

        self.runner = DjangoTestSuiteRunner(interactive=False)
        self.runner.setup_test_environment()
        commands = management.get_commands() # load all commands first
        is_sqlite = settings.DATABASES.get('default', {}).get('ENGINE', '')\
                            .endswith('sqlite3')
        wrap_database()
        try:
            db_postfix = getattr(self.config, 'slaveinput', {}).get("slaveid", "")
            monkey_patch_creation_for_db_reuse(db_postfix
                                             if not is_sqlite else None)
            if 'south' in settings.INSTALLED_APPS:
                from south.management.commands import patch_for_test_db_setup
                if is_sqlite:
                    # dont use migration on in-memory sqlite as its useless
                    management._commands['syncdb'] = 'django.core'
                    self.runner.setup_databases()
                else:
                    patch_for_test_db_setup()
                    self.runner.setup_databases()
                    management.call_command('migrate', verbosity=0)
            else:
                self.runner.setup_databases()
        except SystemExit:
            raise pytest.UsageError('failed to created database')

    def pytest_pycollect_makemodule(self, path, parent):
        return Module(path, parent)


    @pytest.mark.tryfirst # or trylast as it was ?
    def pytest_sessionstart(self, session):
        # turn off debug toolbar to speed up testing
        middlewares = []
        for mid in settings.MIDDLEWARE_CLASSES:
            if not mid.startswith('debug_toolbar'):
                middlewares.append(mid)
        settings.MIDDLEWARE_CLASSES = middlewares
        for db in connections:
            transaction.enter_transaction_management(using=db)
            transaction.managed(True, using=db)
        disable_transaction_methods()

    def pytest_sessionfinish(self, session):
        self.runner.teardown_test_environment()
        restore_transaction_methods()
        for db in connections:
            transaction.rollback(using=db)
            transaction.leave_transaction_management(using=db)

    # @pytest.mark.trylast
    def pytest_collection_modifyitems(self, items):
        trans_modules = [] # modules with transaction test cases
        for item in items:
            item.module.has_transactions = False
            if item.cls is not None:
                if issubclass(item.cls, TestCase):
                    item.parent.obj._fixture_setup = nop
                    # dont touch transaction
                    item.parent.obj._fixture_teardown = nop
                    # dont close connections
                    item.parent.obj._post_teardown = nop
                elif issubclass(item.cls, TransactionTestCase):
                    item.module.has_transactions = True
                    if item.module not in trans_modules:
                        trans_modules.append(item.module)
        sorted_by_modules = sorted(items, cmp=lambda a,b: -1 if b.module in \
                                    trans_modules else 1)
        items_count = len(items)
        for index, item in enumerate(sorted_by_modules[:]):
            if item.module.has_transactions:
                if items_count == index+1:
                    nextitem = None
                elif items_count > index+1:
                    nextitem = sorted_by_modules[index+1]
                if nextitem is None or \
                        sorted_by_modules[index+1].module != item.module:
                    items_for_sort = []
                    start_index = index
                    trans_item = item
                    while trans_item.module == item.module:
                        items_for_sort.append(trans_item)
                        start_index -= 1
                        trans_item = sorted_by_modules[start_index]
                    # preserve old order but move tests with transaction to the end
                    sorted_items = chain(*[list(i[1]) for i in groupby(items_for_sort,
                             lambda x: x.cls and issubclass(x.cls, TransactionTestCase))])
                    sorted_by_modules[start_index+1:index+1] = list(sorted_items)
        items[:] = sorted_by_modules


    def restore_database(self, item, nextitem):
        for db in connections:
                management.call_command('flush', verbosity=0, interactive=False,
                                        database=db)
        all(i.setup() for i in item.listchain())

    def pytest_runtest_protocol(self, item, nextitem):
        """Clear database if previous test item was from different module and it
        was TransactionTestCase. then run setup on all ascending modules
        """
        if item.cls is not None and is_transaction_test(item.cls):
            if nextitem is None or nextitem.module != item.module:
                if nextitem is not None:
                    item._request.addfinalizer(lambda :self.restore_database(item, nextitem))

    @pytest.mark.tryfirst
    def pytest_pycollect_makeitem(self, collector, name, obj):
        """Shadow builtin unittest makeitem with patched class and function
        """
        try:
            isunit = issubclass(obj, unittest.TestCase)
        except KeyboardInterrupt:
            raise
        except Exception:
            pass
        else:
            if isunit:
                return SUnitTestCase(name, parent=collector)
