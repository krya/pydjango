# -*- coding: utf-8 -*-

import sys
from functools import partial
from importlib import import_module

import pytest

from django.conf import settings
from django.db import connections, transaction, InternalError
from django.core import management, mail
from django.test.runner import DiscoverRunner

from .db_reuse import monkey_patch_creation_for_db_reuse, wrap_database
from .fixtures import Fixtures
from .utils import is_transaction_test, nop


class DjangoPlugin(Fixtures):

    def __init__(self, config):
        self.config = config
        self.check_markers()
        self.configure()
        self.original_connection_close = {}
        try:
            self.live_server_class = import_module(config.option.liveserver_class)
        except ImportError:
            liveserver_class = config.option.liveserver_class.split('.')
            self.live_server_class = getattr(
                import_module('.'.join(liveserver_class[:-1])),
                liveserver_class[-1]
            )

    def check_markers(self):
        self.skip_trans = False
        if 'not transaction' in self.config.option.markexpr or self.config.option.skip_trans:
            self.skip_trans = True

    def configure(self):

        self.runner = DiscoverRunner(
            interactive=False,
            verbosity=self.config.option.verbose
        )
        self.runner.setup_test_environment()
        management.get_commands()  # load all commands first
        is_sqlite = settings.DATABASES.get('default', {}).get('ENGINE', '')\
                            .endswith('sqlite3')
        wrap_database()
        db_postfix = getattr(self.config, 'slaveinput', {}).get("slaveid", "")
        monkey_patch_creation_for_db_reuse(
            db_postfix if not is_sqlite else None,
            force=self.config.option.create_db
        )
        migrate_db = self.config.option.migrate or self.config.option.create_db
        can_migrate = 'south' in settings.INSTALLED_APPS
        if can_migrate:
            from south.management.commands import patch_for_test_db_setup
            patch_for_test_db_setup()
        try:
            self.runner.setup_databases()
            if migrate_db and can_migrate:
                management.call_command('migrate', verbosity=self.config.option.verbose)
        except Exception:
            raise pytest.UsageError(sys.exc_info()[1])

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        for db in connections:
            conn = connections[db]
            conn.set_autocommit(
                False, force_begin_transaction_with_broken_autocommit=True
            )
            conn.in_atomic_block = True
            self.original_connection_close[db] = conn.close
            conn.close = nop

    def pytest_sessionfinish(self, session):
        self.runner.teardown_test_environment()
        for db in connections:
            connections[db].in_atomic_block = False
            transaction.rollback(using=db)
            connections[db].in_atomic_block = True
            if self.original_connection_close:
                connections[db].close = self.original_connection_close[db]

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

    def schedule_savepoints(self, item):
        for db in connections:
            if not hasattr(item, 'pydjango_savepoints'):
                item.pydjango_savepoints = {}
            item.pydjango_savepoints[db] = transaction.savepoint(using=db)

    def rollback_savepoints(self, item):
        for db in connections:
            sid = item.pydjango_savepoints.pop(db)
            try:
                transaction.savepoint_rollback(sid, using=db)
            except InternalError:
                print(f'Failed to rollback savepoint - {sid}')
                transaction.rollback(using=db)

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item):
        mail.outbox = []
        if 'transaction' in item.keywords and self.skip_trans:
            pytest.skip('excluding transaction test')
        self.schedule_savepoints(item)

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_teardown(self, item, nextitem):
        if hasattr(item, 'pydjango_savepoints'):
            self.rollback_savepoints(item)
