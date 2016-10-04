# -*- coding: utf-8 -*-

import threading
import errno
import socket

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.test.testcases import _MediaFilesHandler, QuietWSGIRequestHandler
from django.core.handlers.wsgi import WSGIHandler


def supported():
    import django.test.testcases

    return hasattr(django.test.testcases, 'LiveServerThread')


class LiveServerThread(threading.Thread):
    """
    Thread for running a live http server while the tests are running.
    """

    def __init__(self, server_class, addr):
        self.is_ready = threading.Event()
        self.server_class = server_class
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

    def start_http_server(self, port, handler):
        try:
            return self.server_class((self.host, port), handler)
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                # This port is already in use, so we go on and try with
                # the next one in the list.
                return
            else:
                # Either none of the given ports are free or the error
                # is something else than "Address already in use". So
                # we let that error bubble up to the main thread.
                raise

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
                if hasattr(self.server_class, 'set_app'):
                    # should set handlers specified above a bit later as
                    # this one takes QuietWSGIRequestHandler
                    self.httpd = self.start_http_server(port, QuietWSGIRequestHandler)
                else:
                    self.httpd = self.start_http_server(port, handler)
                if self.httpd is None:
                    continue
                # A free port was found.
                self.port = port
                break
            if hasattr(self.httpd, 'set_app'):
                self.httpd.set_app(handler)
            self.is_ready.set()
            self.httpd.serve_forever()
        except Exception as e:
            self.error = e
            self.is_ready.set()

    def join(self, timeout=None):
        if hasattr(self, 'httpd'):
            # Stop the WSGI server
            if hasattr(self.httpd, 'shutdown'):
                self.httpd.shutdown()
                self.httpd.server_close()
            else:
                self.httpd.stop()
        super(LiveServerThread, self).join(timeout)


class LiveServer(object):
    """The liveserver fixture

    This is the object which is returned to the actual user when they
    request the ``live_server`` fixture.  The fixture handles creation
    and stopping however.
    """
    server_thread = LiveServerThread

    def __init__(self, server_class, addr):
        self.thread = self.server_thread(server_class, addr)
        self.thread.daemon = True
        self.thread.start()
        self.thread.is_ready.wait()
        if self.thread.error:
            raise self.thread.error

    def stop(self):
        """Stop the server"""
        self.thread.join(1)

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
