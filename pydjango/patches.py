# -*- coding: utf-8 -*-

import pytest
from _pytest.unittest import UnitTestCase, TestCaseFunction

from django.db import connections, transaction
from django.core import mail

from .utils import is_transaction_test, nop


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
            except (ValueError, AttributeError):
                pass
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


class Instance(SavepointMixin, pytest.Instance):
    pass


class Class(SavepointMixin, pytest.Class):

    def setup(self):
        if not hasattr(self.obj, 'setup_class'):
            self.need_savepoint = False
        return super(Class, self).setup()


class SUnitTestCase(SavepointMixin, UnitTestCase):

    def setup(self):
        if is_transaction_test(self.cls):
            self.need_savepoint = False
        else:
            self.obj._fixture_setup = nop
            # dont touch transaction
            self.obj._fixture_teardown = nop
            # dont close connections
            self.obj._post_teardown = nop
        return super(SUnitTestCase, self).setup()

    def collect(self):
        for function in super(SUnitTestCase, self).collect():
            if is_transaction_test(function.parent.obj):
                self.keywords['transaction'] = True
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

    def collect(self, *args, **kwargs):
        "Mark module if it contains transaction tests"
        items = super(Module, self).collect(*args, **kwargs)
        self.obj.has_transactions = False
        if any([i for i in items if i.cls and is_transaction_test(i.cls)]):
            self.obj.has_transactions = True
            self.need_savepoint = False
        return items
