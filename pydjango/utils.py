# -*- coding: utf-8 -*-

from django.test.testcases import TransactionTestCase, TestCase

def nop(*args, **kwargs):
    return


def is_transaction_test(cls):
    return issubclass(cls, TransactionTestCase) and not issubclass(cls, TestCase)
