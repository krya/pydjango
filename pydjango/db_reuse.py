"""Functions to aid in preserving the test database between test runs.

The code in this module is heavily inspired by django-nose:
https://github.com/jbalogh/django-nose/
"""

import types

from django.conf import settings
from django.db import connections, transaction
from django.db.backends.sqlite3.base import DatabaseOperations as BDO

from .utils import nop


def can_support_db_reuse(connection):
    """Return whether it makes any sense to use REUSE_DB with the backend of a connection."""
    # This is a SQLite in-memory DB. Those are created implicitly when
    # you try to connect to them, so our test below doesn't work.
    return connection.creation._get_test_db_name() != ':memory:'


def test_database_exists_from_previous_run(connection):
    # Check for sqlite memory databases
    if not can_support_db_reuse(connection):
        return False

    # Try to open a cursor to the test database
    orig_db_name = connection.settings_dict['NAME']
    connection.settings_dict['NAME'] = connection.creation._get_test_db_name()
    try:
        connection.cursor()
        return True
    except Exception:
        return False
    finally:
        connection.close()
        connection.settings_dict['NAME'] = orig_db_name


def create_test_db(self, verbosity=1, autoclobber=False, serialize=False, keepdb=False):
    """
    This method is a monkey patched version of create_test_db that
    will not actually create a new database, but just reuse the
    existing.
    """
    test_database_name = self._get_test_db_name()
    self.connection.settings_dict['NAME'] = test_database_name

    if verbosity >= 1:
        test_db_repr = ''
        if verbosity >= 2:
            test_db_repr = " ('%s')" % test_database_name
        print("Re-using existing test database for alias '%s'%s..." % (
            self.connection.alias, test_db_repr))

    if hasattr(self.connection.features, 'confirm'):
        # django < 1.5
        self.connection.features.confirm()

    return test_database_name


def _get_test_db_name(self):
    name = super(self.__class__, self)._get_test_db_name()
    return name + self.db_postfix


def monkey_patch_creation_for_db_reuse(db_postfix, force=False):
    for alias in connections:
        connection = connections[alias]
        creation = connection.creation
        if db_postfix:
            creation.db_postfix = db_postfix
            creation._get_test_db_name = types.MethodType(_get_test_db_name, creation)
        if test_database_exists_from_previous_run(connection):
            # Make sure our monkey patch is still valid in the future
            assert hasattr(creation, 'create_test_db')
            if not force:
                creation.create_test_db = types.MethodType(create_test_db, creation)


class BaseDatabaseOperations(BDO):

    def savepoint_create_sql(self, sid):
        return "SAVEPOINT %s" % sid

    def savepoint_commit_sql(self, sid):
        return "RELEASE SAVEPOINT %s" % sid

    def savepoint_rollback_sql(self, sid):
        return "ROLLBACK TO SAVEPOINT %s" % sid


def wrap_database():
    connections._connections = connections._connections.default
    for db in connections.all():
        if db.vendor == 'sqlite':
            options = settings.DATABASES[db.alias].get("OPTIONS", {})
            # isolation_level should be None to use savepoints in sqlite
            options.update({'isolation_level': None})
            settings.DATABASES[db.alias]['OPTIONS'] = options
            db.features.uses_savepoints = True
            db.ops = BaseDatabaseOperations(db.alias)
        if hasattr(db, 'inc_thread_sharing'):
            db.inc_thread_sharing()
        else:
            db.allow_thread_sharing = True
        db.abort = nop
        db.close_if_unusable_or_obsolete = nop
