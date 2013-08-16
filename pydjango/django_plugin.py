# -*- coding: utf-8 -*-

import sys

from itertools import groupby
import unittest
import thread

import pytest

from django.conf import settings
from django.db import connections, transaction
from django.core import management
from django.test.testcases import (TestCase,
                                   disable_transaction_methods,
                                    restore_transaction_methods)
from django.test.simple import DjangoTestSuiteRunner


from .patches import Module, SUnitTestCase
from .db_reuse import monkey_patch_creation_for_db_reuse, wrap_database
from .fixtures import Fixtures
from .utils import nop, is_transaction_test


class DjangoPlugin(Fixtures):

    def __init__(self, config):
        self.config = config
        self.check_markers()
        self.configure()

    def check_markers(self):
        self.skip_trans = False
        if 'not transaction' in self.config.option.markexpr or self.config.option.skip_trans:
            self.skip_trans = True

    def configure(self):

        self.runner = DjangoTestSuiteRunner(interactive=False)
        self.runner.setup_test_environment()
        management.get_commands()  # load all commands first
        is_sqlite = settings.DATABASES.get('default', {}).get('ENGINE', '')\
                            .endswith('sqlite3')
        try:
            wrap_database()
            db_postfix = getattr(self.config, 'slaveinput', {}).get("slaveid", "")
            monkey_patch_creation_for_db_reuse(db_postfix if not is_sqlite else None,
                                               force=self.config.option.create_db)
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

        except (SystemExit, Exception):
            raise pytest.UsageError(sys.exc_info()[1])

    def pytest_pycollect_makemodule(self, path, parent):
        return Module(path, parent)

    @pytest.mark.tryfirst  # or trylast as it was ?
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
        # disable_transaction_methods()

    def pytest_sessionfinish(self, session):
        self.runner.teardown_test_environment()
        restore_transaction_methods()
        for db in connections:
            if connections[db]._thread_ident == thread.get_ident():
                # only rollback if wrapper was created in same thread
                transaction.rollback(using=db)
                transaction.leave_transaction_management(using=db)

    @pytest.mark.trylast
    def pytest_collection_modifyitems(self, items):
        trans_items = []
        non_trans = []
        for index, item in enumerate(items):
            if item.module.has_transactions:
                trans_items.append(item)
            else:
                non_trans.append(item)
        sorted_trans = []
        for module, iterator in groupby(trans_items[:], lambda x: x.module):
            for item, it in groupby(iterator, lambda x: x.cls and is_transaction_test(x.cls)):
                sorted_trans.extend(it)
        sorted_by_modules = non_trans + sorted_trans
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
                    item._request.addfinalizer(lambda: self.restore_database(item, nextitem))

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

    @pytest.mark.tryfirst
    def pytest_runtest_setup(self, item):
        if 'transaction' in item.keywords and self.skip_trans:
            pytest.skip('excluding transaction test')
