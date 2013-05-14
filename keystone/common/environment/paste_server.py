import sys

from paste.httpserver import WSGIServer
from paste.httpserver import WSGIHandler

from keystone.common import config
from keystone.common import logging

from OpenSSL import SSL

CONF = config.CONF
LOG = logging.getLogger(__name__)

use_process = False

if use_process:
    from multiprocessing import Process as Concurrent
else:
    # using threads does not respond to KeyboardInterrupt
    # so will server forever and not be cancellable
    from threading import Thread as Concurrent


# Subclass to workaround: https://bugs.launchpad.net/pyopenssl/+bug/900792
class PasteServer(WSGIServer):
    def shutdown_request(self, request):
        request.shutdown()


class Server(Concurrent):

    def __init__(self, application, host=None, port=None, threads=0, key=None):
        Concurrent.__init__(self)

        self.application = application
        self.host = host
        self.port = port
        self.cert_required = False
        self.daemon = True
        self.server = None
        self.ssl_context = None

    def start(self, **kwargs):
        if self.ssl_context:
            server_class = PasteServer
        else:
            server_class = WSGIServer

        self.server = server_class(self.application, (self.host, self.port),
                                   WSGIHandler, self.ssl_context,
                                   request_queue_size=1)
        self.server.daemon_threads = True

        self.host, self.port = self.server.server_address

        super(Server, self).start()

    def set_ssl(self, certfile, keyfile=None,
                ca_certs=None, cert_required=True):
        if not self.ssl_context:
            self.ssl_context = SSL.Context(SSL.SSLv23_METHOD)
            self.ssl_context.set_options(SSL.OP_NO_SSLv2)

        if keyfile:
            self.ssl_context.use_privatekey_file(keyfile)

        if certfile:
            self.ssl_context.use_certificate_file(certfile)

        if ca_certs:
            self.ssl_context.load_verify_locations(ca_certs)

        verify_options = SSL.VERIFY_PEER

        if cert_required:
            verify_options |= SSL.VERIFY_FAIL_IF_NO_PEER_CERT

        self.ssl_context.set_verify(verify_options,
                                    self._ssl_verify_callback)

    def _ssl_verify_callback(self, conn, cert, err_no, depth, result):
        return result

    def run(self, key=None, backlog=128):
        """Run a WSGI server with the given application."""
        LOG.debug(_('Starting %(arg0)s on %(host)s:%(port)s') %
                  {'arg0': sys.argv[0],
                   'host': self.host,
                   'port': self.port})

        self.server.serve_forever()

    def kill(self):
        if use_process:
            self.terminate()
        else:
            self.server.shutdown()

        self.join()

