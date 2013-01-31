# -*- coding: utf-8 -*-

import inspect

import pytest
from _pytest.unittest import UnitTestCase, TestCaseFunction

from django.conf import settings
from django.db import connections, transaction
from django.db.backends.sqlite3.base import DatabaseOperations as BDO
from django.core import mail

from django.test.testcases import TransactionTestCase, TestCase

class BaseDatabaseOperations(BDO):

    def savepoint_create_sql(self, sid):
        return "SAVEPOINT %s" % sid
    def savepoint_commit_sql(self, sid):
        return "RELEASE SAVEPOINT %s" % sid
    def savepoint_rollback_sql(self, sid):
        return "ROLLBACK TO SAVEPOINT %s" % sid

def patch_sqlite():
    for db in connections:
        if connections[db].vendor == 'sqlite':
            options = settings.DATABASES[db].get("OPTIONS", {})
            # isolation_level should be None to use savepoints in sqlite
            options.update({'isolation_level':None})
            settings.DATABASES[db]['OPTIONS'] = options
            connections[db].features.uses_savepoints = True
            connections[db].ops = BaseDatabaseOperations()

def make_savepoints():
    savepoints = {}
    for db in connections:
        savepoints[db] = transaction.savepoint(using=db)
    return savepoints

def rollback_savepoints(savepoints):
    for db in savepoints:
        transaction.savepoint_rollback(savepoints[db], using=db)

class SavepointMixin(object):

    def Function(self, *args, **kwargs):
        return Function(*args, **kwargs)

    def Instance(self, *args, **kwargs):
        return Instance(*args, **kwargs)

    def setup(self, *args, **kwargs):
        if self.cls is None or issubclass(self.cls, TestCase) or not issubclass(self.cls,TransactionTestCase):
            self.savepoints = make_savepoints()
        return super(SavepointMixin, self).setup(*args, **kwargs)

    def teardown(self, *args, **kwargs):
        if self.cls is None or issubclass(self.cls, TestCase) or not issubclass(self.cls,TransactionTestCase):
            rollback_savepoints(self.savepoints)
        return super(SavepointMixin, self).teardown(*args, **kwargs)

class Function(SavepointMixin, pytest.Function):
    def setup(self, *args, **kwargs):
        mail.outbox = []
        return super(Function, self).setup(*args, **kwargs)

class Instance(SavepointMixin, pytest.Instance):pass

class Class(SavepointMixin, pytest.Class):pass

class SUnitTestCase(SavepointMixin, UnitTestCase):

    def collect(self):
        for function in super(SUnitTestCase, self).collect():
            yield STestCaseFunction(name=function.name, parent=function.parent)

class STestCaseFunction(SavepointMixin, TestCaseFunction):pass


class Module(pytest.Module):

    Class = Class
    Instance = Instance
    Function = Function

    def setup(self):
        if hasattr(self.obj, 'setup_module'):
            self.savepoints = make_savepoints()
        return super(Module, self).setup()

    def teardown(self):
        res = super(Module, self).teardown()
        if hasattr(self.obj, 'setup_module') and not getattr(self.obj, 'has_transactions', False):
            rollback_savepoints(self.savepoints)
        return res


