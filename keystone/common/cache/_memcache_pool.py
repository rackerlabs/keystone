# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Thread-safe connection pool for python-memcached."""

import contextlib
import itertools
import threading
import time

import memcache

from keystone.i18n import _LE
from keystone.openstack.common import log


LOG = log.getLogger(__name__)

# NOTE(yorik-sar): This 'class' is taken from
# http://stackoverflow.com/a/22520633/238308 . Don't inherit client from
# threading.local so that we can reuse clients in different threads
MemcacheClient = type('MemcacheClient', (object,),
                      dict(memcache.Client.__dict__))


class MemcacheConnectionPool(object):
    def __init__(self, url, max_pool_size, client_ttl, debug=False,
                 **arguments):
        self._free_pool = []
        self._server_list = [0] * len(url)
        self._condition = threading.Condition()
        self.acquired = 0
        self.url = url
        self.max_pool_size = max_pool_size
        self.client_ttl = client_ttl
        self.arguments = arguments
        self._debug_pool = debug

    def _debug_logger(self, msg, *args, **kwargs):
        if self._debug_pool:
            # NOTE(morganfainberg): Do not do the debug work unless we are
            # actually debugging the pool.
            thread_id = threading.current_thread().ident
            prefix = ('Memcached client pool %(pool)s, thread %(thread)s: ' %
                      {'pool': id(self), 'thread': thread_id})
            LOG.debug(prefix + msg, *args, **kwargs)

    def _create_connection(self):
        conn = MemcacheClient(self.url, **self.arguments)
        self._debug_logger('Creating new memcached client: %s', id(conn))
        return conn

    def _destroy_connection(self, conn):
        self._debug_logger('Destroying memcached client: %s', id(conn))
        try:
            conn.disconnect_all()
        except Exception as e:
            # Catch and log the exception, this should not explode ever, but
            # make sure the error doesn't break the pool.
            self._debug_logger('Error when destroying connection '
                               '%(conn)s: %(err)s', {'conn': id(conn),
                                                     'err': str(e)})

    def acquire(self):
        with self._condition:
            self._debug_logger('Acquiring memcached client connection.')
            conn = None
            now = time.time()
            while conn is None:
                while (not self._condition and
                       self.acquired >= self.max_pool_size):
                    # Wait for either a free connection or free space for a new
                    # connection.
                    self._condition.wait()
                try:
                    # Grab an active connection
                    ttl, conn = self._free_pool.pop()
                    if ttl is not None and ttl < now:
                        # Do not used expired connections. Each client has a
                        # maximum TTL it can sit in the free pool unused, this
                        # is to limit potential timeouts / socket closures and
                        # delays or errors in responding due to these timeouts.
                        self._destroy_connection(conn)
                        conn = None
                except IndexError:
                    # There are no active connections available, create a new
                    # connection
                    conn = self._create_connection()
            for deaduntil, host in zip(self._server_list,
                                       conn.servers):
                # Ensure the deaduntil is propagated from the pool.
                if deaduntil > now and host.deaduntil <= now:
                    host.mark_dead('propagating death mark from the pool')
                host.deaduntil = deaduntil
            self.acquired += 1
            self._debug_logger('Acquired connection %s', id(conn))
            return conn

    def release(self, conn):
        with self._condition:
            try:
                # NOTE(morganfainberg): This is all house keeping and tracking
                # the dead servers. This is so we can limit delays when talking
                # to a server because we already know it's dead. If all servers
                # are dead, the logic will fallback to the socket timeout
                # instead of the dead-server delay.
                now = time.time()
                for i, deaduntil, host in zip(itertools.count(),
                                              self._server_list,
                                              conn.servers):
                    if deaduntil <= now:
                        if host.deaduntil > now:
                            self._server_list[i] = host.deaduntil
                            self._debug_logger('Marked host %s dead until %s',
                                               self.url[i], host.deaduntil)
                        else:
                            self._server_list[i] = 0
                if all(deaduntil > now for deaduntil in self._server_list):
                    self._debug_logger('All hosts are dead. Falling back to '
                                       'socket timeout.')
                    self._server_list = [0] * len(self.url)
            finally:
                self._debug_logger('Releasing connection: %s', id(conn))
                self._free_pool.append((time.time() + self.client_ttl, conn))
                self.acquired -= 1
                self._condition.notify_all()

    @contextlib.contextmanager
    def get(self):
        conn = self.acquire()
        try:
            yield conn
        finally:
            self.release(conn)
