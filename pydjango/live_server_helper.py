# -*- coding: utf-8 -*-

import threading
import errno

import pytest

from django.db import connections
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.test.testcases import _MediaFilesHandler, StoppableWSGIServer, QuietWSGIRequestHandler
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import (WSGIRequestHandler, WSGIServer,
                                          WSGIServerException)


def supported():
    import django.test.testcases

    return hasattr(django.test.testcases, 'LiveServerThread')


class LiveServerThread(threading.Thread):
    """
    Thread for running a live http server while the tests are running.
    """

    def __init__(self, addr):
        self.is_ready = threading.Event()
        self.error = None
        self.possible_ports = []
        try:
            self.host, port_ranges = addr.split(':')
            for port_range in port_ranges.split(','):
                # A port range can be of either form: '8000' or '8000-8010'.
                extremes = list(map(int, port_range.split('-')))
                assert len(extremes) in [1, 2]
                if len(extremes) == 1:
                    # Port range of the form '8000'
                    self.possible_ports.append(extremes[0])
                else:
                    # Port range of the form '8000-8010'
                    for port in range(extremes[0], extremes[1] + 1):
                        self.possible_ports.append(port)
        except Exception:
            raise Exception('Invalid address ("%s") for live server.' % addr)
        super(LiveServerThread, self).__init__()

    def run(self):
        """
        Sets up the live server and databases, and then loops over handling
        http requests.
        """
        try:
            # Create the handler for serving static and media files
            handler = StaticFilesHandler(_MediaFilesHandler(WSGIHandler()))

            # Go through the list of possible ports, hoping that we can find
            # one that is free to use for the WSGI server.
            for index, port in enumerate(self.possible_ports):
                try:
                    self.httpd = StoppableWSGIServer(
                        (self.host, port), QuietWSGIRequestHandler)
                except WSGIServerException as e:
                    if (index + 1 < len(self.possible_ports) and
                        hasattr(e.args[0], 'errno') and
                            e.args[0].errno == errno.EADDRINUSE):
                        # This port is already in use, so we go on and try with
                        # the next one in the list.
                        continue
                    else:
                        # Either none of the given ports are free or the error
                        # is something else than "Address already in use". So
                        # we let that error bubble up to the main thread.
                        raise
                else:
                    # A free port was found.
                    self.port = port
                    break

            self.httpd.set_app(handler)
            self.is_ready.set()
            self.httpd.serve_forever()
        except Exception as e:
            self.error = e
            self.is_ready.set()

    def join(self, timeout=None):
        if hasattr(self, 'httpd'):
            # Stop the WSGI server
            self.httpd.shutdown()
            self.httpd.server_close()
        super(LiveServerThread, self).join(timeout)


class LiveServer(object):
    """The liveserver fixture

    This is the object which is returned to the actual user when they
    request the ``live_server`` fixture.  The fixture handles creation
    and stopping however.
    """

    def __init__(self, addr):
        self.thread = LiveServerThread(addr)
        self.thread.daemon = True
        self.thread.start()
        self.thread.is_ready.wait()
        if self.thread.error:
            raise self.thread.error

    def stop(self):
        """Stop the server"""
        self.thread.join()

    @property
    def url(self):
        return 'http://%s:%s' % (self.thread.host, self.thread.port)

    def __unicode__(self):
        return self.url

    __str__ = __unicode__

    def __repr__(self):
        return '<LiveServer listening at %s>' % self

    def __add__(self, other):
        # Support string concatenation
        return self + other
