# -*- coding: utf-8 -*-

import pytest
from _pytest.unittest import UnitTestCase, TestCaseFunction

import django
from django.conf import settings
from django.db import connections, transaction
from django.db.backends.sqlite3.base import DatabaseOperations as BDO
from django.core import mail

from .utils import is_transaction_test


class BaseDatabaseOperations(BDO):

    def savepoint_create_sql(self, sid):
        return "SAVEPOINT %s" % sid
    def savepoint_commit_sql(self, sid):
        return "RELEASE SAVEPOINT %s" % sid
    def savepoint_rollback_sql(self, sid):
        return "ROLLBACK TO SAVEPOINT %s" % sid

def cursor_wrapper(function):
    def wraps(*args, **kwargs):
        cursor = function(*args, **kwargs)
        if hasattr(function.im_self, 'setup_savepoints'):
            node_list = function.im_self.setup_savepoints[:]
            function.im_self.setup_savepoints = []
            for node in node_list:
                node.savepoints = {}
                for db in connections:
                    node.savepoints[db] = transaction.savepoint(using=db)
        return cursor
    return wraps

def patch_sqlite():
    for db in connections:
        if connections[db].vendor == 'sqlite':
            options = settings.DATABASES[db].get("OPTIONS", {})
            # isolation_level should be None to use savepoints in sqlite
            options.update({'isolation_level':None})
            settings.DATABASES[db]['OPTIONS'] = options
            connections[db].features.uses_savepoints = True
            if django.VERSION < (1,4) :
                connections[db].ops = BaseDatabaseOperations()
            else:
                connections[db].ops = BaseDatabaseOperations(db)
        connections[db]._cursor = cursor_wrapper(connections[db]._cursor)


class SavepointMixin(object):

    def __init__(self, *args, **kwargs):
        super(SavepointMixin, self).__init__(*args, **kwargs)
        self.need_savepoint = True
        self.savepoints = {}

    def Function(self, *args, **kwargs):
        return Function(*args, **kwargs)

    def Instance(self, *args, **kwargs):
        return Instance(*args, **kwargs)

    def schedule_savepoints(self):
        for db in connections:
            if not hasattr(connections[db], 'setup_savepoints'):
                connections[db].setup_savepoints = []
            connections[db].setup_savepoints.append(self)

    def rollback_savepoints(self):
        for db in connections:
            try:
                connections[db].setup_savepoints.pop(connections[db].setup_savepoints.index(self))
            except ValueError:pass
            if self.savepoints:
                transaction.savepoint_rollback(self.savepoints[db], using=db)

    def setup(self, *args, **kwargs):
        if self.need_savepoint:
            self.schedule_savepoints()
        return super(SavepointMixin, self).setup(*args, **kwargs)

    def teardown(self, *args, **kwargs):
        if self.cls is None or hasattr(self, 'savepoints'):
            self.rollback_savepoints()
        return super(SavepointMixin, self).teardown(*args, **kwargs)

class Function(SavepointMixin, pytest.Function):
    def setup(self, *args, **kwargs):
        mail.outbox = []
        return super(Function, self).setup(*args, **kwargs)

class Instance(SavepointMixin, pytest.Instance):pass

class Class(SavepointMixin, pytest.Class):

    def setup(self):
        if not hasattr(self.obj, 'setup_class'):
            self.need_savepoint = False
        return super(Class, self).setup()

class SUnitTestCase(SavepointMixin, UnitTestCase):

    def setup(self):
        if is_transaction_test(self.cls):
            self.need_savepoint = False
        return super(SUnitTestCase, self).setup()

    def collect(self):
        for function in super(SUnitTestCase, self).collect():
            yield STestCaseFunction(name=function.name, parent=function.parent)

class STestCaseFunction(SavepointMixin, TestCaseFunction):
    def setup(self):
        if is_transaction_test(self.cls):
            self.need_savepoint = False
        return super(STestCaseFunction, self).setup()


class Module(SavepointMixin, pytest.Module):

    Class = Class
    Function = Function

    def setup(self):
        if not hasattr(self.obj, 'setup_module'):
            self.need_savepoint = False
        return super(Module, self).setup()



