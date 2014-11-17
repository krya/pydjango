About
-----
This is a `py.test <http://pytest.org/>`_ plugin to help you test your django application.

supports python 2.6-3.2 and django 1.4-1.5

.. image:: https://travis-ci.org/krya/pydjango.png
   :target: https://travis-ci.org/krya/pydjango

Features
--------
* support `pytest-xdist <http://pypi.python.org/pypi/pytest-xdist>`_
    currently each node will create its own database (there is not way to run transaction tests synchronously on a single node)
* support for nested `setup_module/setup_class <http://pytest.org/latest/xunit_setup.html>`_
    every module or class is surrounded with savepoint
* lazy savepoints
    savepoints won't be created unless your test function and/or fixture accessing database saving few round-trips
* djangos TransactionTestCase, TestCase and plain unittests TestCase are supported.

Installation
------------
``pip install git+https://github.com/krya/pydjango#egg=pydjango``

Usage
-----
First of all you need to make this plugin aware of your django settings. To do so you have few options:

* make an environment variable: ::

    export DJANGO_SETTINGS_MODULE=myproject.settings

* pass settings path to py.test invocation: ::

    py.test --django-settings=myproject.settings

* make a `pytest.ini` file in root folder with following content: ::

    [pytest]
    DJANGO_SETTINGS_MODULE=myproject.settings

* and finally you can set up your `settings in python code <https://docs.djangoproject.com/en/1.4/topics/settings/#using-settings-without-setting-django-settings-module>`_. Just make a `conftest.py`
  file in root folder with: ::

    from django.conf import settings

    def pytest_configure():
        settings.configure(DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3'}})


Now can run tests with ``py.test`` conmmand.


Available fixtures
------------------

* client
    `Client instance <https://docs.djangoproject.com/en/1.4/topics/testing/#module-django.test.client>`_
* rf
    `RequestFactory instance <https://docs.djangoproject.com/en/1.4/topics/testing/#django.test.client.RequestFactory:>`_
* test_user
    user instace with username `test`
* admin_user
    superuser instance with username `admin`
* anon_user
    `AnonymousUser instance <https://docs.djangoproject.com/en/1.4/topics/auth/#django.contrib.auth.models.AnonymousUser>`_
* settings
    django's settings module
* uclient
    a client instance with logged in test_user
* aclient
    a client instance with logged in admin_user

both `uclient` and `aclient` are logged in using ``django.contrib.auth.backends.ModelBackend``.

There are also imported apps available as fixtures named by subpackage name. So for instance if you have
`django.contrib.auth` in your `INSTALLED_APPS` you can use that package in your tests
without importing it in every test function: ::

    def test_smth(auth):
        assert auth.models.User.objects.count() == 0


You can even use model's name defined in your project as a fixture: ::

    def test_my_model(User):
        assert User.objects.count() == 0


Comman line options
-------------------

* `--create-db`
    Force database creation. Destroys db if it exists from previous run
* `--skip-trans`
    skip all `transactional` tests (LiveServerTestCase or TransactionTestCase)
* `--migrate`
    runs syncdb and south migrations (may be slow in big projects so let user decide). does nothing when `--create-db` used
