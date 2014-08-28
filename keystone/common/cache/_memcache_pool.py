# Copyright 2014 Mirantis Inc
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

# NOTE(yorik-sar): this file is copied between keystone and keystonemiddleware
# and should be kept in sync until we can use external library for this.

import abc
import collections
import contextlib
import itertools
import logging
import threading
import time

import memcache
import six

from keystone.openstack.common import log


LOG = log.getLogger(__name__)

# This 'class' is taken from http://stackoverflow.com/a/22520633/238308
# Don't inherit client from threading.local so that we can reuse clients in
# different threads
_MemcacheClient = type('_MemcacheClient', (object,),
                       dict(memcache.Client.__dict__))

_PoolItem = collections.namedtuple('_PoolItem', ['ttl', 'connection'])


@six.add_metaclass(abc.ABCMeta)
class ConnectionPool(object):
    def __init__(self, maxsize, unused_timeout):
        self._maxsize = maxsize
        self._unused_timeout = unused_timeout
        self._acquired = 0
        self._free_pool = []
        self._no_free_condition = threading.Condition()

    @abc.abstractmethod
    def _create_connection(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _destroy_connection(self, conn):
        raise NotImplementedError

    def _debug_logger(self, msg, *args, **kwargs):
        if LOG.isEnabledFor(logging.DEBUG):
            thread_id = threading.current_thread().ident
            args = (id(self), thread_id) + args
            prefix = 'Memcached pool %s, thread %s: '
            LOG.debug(prefix + msg, *args, **kwargs)

    def acquire(self):
        with self._no_free_condition:
            self._debug_logger('Acquiring connection')
            # Wait for either free connection or free space for a new one
            while not self._free_pool and self._acquired >= self._maxsize:
                self._no_free_condition.wait()
            try:
                # Get a free connection from the pool
                conn = self._free_pool.pop().connection
            except IndexError:
                # No free connections, create a new one.
                conn = self._create_connection()
                self._debug_logger('Created a new connection %s', id(conn))
            self._acquired += 1
            self._debug_logger('Acquired connection %s', id(conn))
            return conn

    def release(self, conn):
        with self._no_free_condition:
            self._debug_logger('Releasing connection %s', id(conn))
            # Return connection to pool
            self._free_pool.append(_PoolItem(
                ttl=time.time() + self._unused_timeout,
                connection=conn,
            ))
            self._acquired -= 1
            self._cleanup_pool()
            # Notify waiting getters
            self._no_free_condition.notify_all()

    def _cleanup_pool(self):
        now = time.time()
        non_expired_idx = None  # None means all connections expired
        for idx, item in enumerate(self._free_pool):
            if item.ttl >= now:
                # Find the index of the last non-expired connection
                non_expired_idx = idx  # any integer means we found good ones
                break
        if non_expired_idx == 0:  # but not None!
            return  # all connections are good, nothing to do
        for item in self._free_pool[:non_expired_idx]:
            conn = item.connection
            self._debug_logger('Reaping connection %s', id(conn))
            self._destroy_connection(conn)
        self._free_pool[:non_expired_idx] = []

    @contextlib.contextmanager
    def get(self):
        conn = self.acquire()
        try:
            yield conn
        finally:
            self.release(conn)


class DumbPool(ConnectionPool):
    def __init__(self, *args, **kwargs):
        super(DumbPool, self).__init__(*args, **kwargs)
        self._count = itertools.count()

    def _create_connection(self):
        return next(self._count)

    def _destroy_connection(cls, conn):
        pass


class MemcacheClientPool(ConnectionPool):
    def __init__(self, urls, arguments, **kwargs):
        super(MemcacheClientPool, self).__init__(**kwargs)
        self.urls = urls
        self._arguments = arguments
        # NOTE(morganfainberg): The host objects expect an int for the
        # deaduntil value. Initialize this at 0 for each host with 0 indicating
        # the host is not dead.
        self._hosts_deaduntil = [0] * len(urls)

    def _create_connection(self):
        return _MemcacheClient(self.urls, **self._arguments)

    def _destroy_connection(self, conn):
        conn.disconnect_all()

    def acquire(self):
        conn = super(MemcacheClientPool, self).acquire()
        try:
            with self._no_free_condition:
                # Propagate host state known to us to this client's list
                now = time.time()
                for deaduntil, host in zip(self._hosts_deaduntil,
                                           conn.servers):
                    if deaduntil > now and host.deaduntil <= now:
                        host.mark_dead('propagating death mark from the pool')
                    host.deaduntil = deaduntil
        except Exception:
            # We need to be sure that connection doesn't leak from the pool.
            # This code runs before we enter context manager's try-finally
            # block, so we need to explicitly release it here
            super(MemcacheClientPool, self).release(conn)
            raise
        return conn

    def release(self, conn):
        try:
            with self._no_free_condition:
                # If this client found that one of the hosts is dead, mark it
                # as such in our internal list
                now = time.time()
                for i, deaduntil, host in zip(itertools.count(),
                                              self._hosts_deaduntil,
                                              conn.servers):
                    # Do nothing if we already know this host is dead
                    if deaduntil <= now:
                        if host.deaduntil > now:
                            self._hosts_deaduntil[i] = host.deaduntil
                            self._debug_logger(
                                'Marked host %s dead until %s',
                                self.urls[i], host.deaduntil)
                        else:
                            self._hosts_deaduntil[i] = 0
                # If all hosts are dead we should forget that they're dead.
                # This way we won't get completely shut off until dead_retry
                # seconds pass, but will be checking servers as frequent as we
                # can (over way smaller socket_timeout)
                if all(deaduntil > now for deaduntil in self._hosts_deaduntil):
                    self._debug_logger('All hosts are dead. Marking them as '
                                       'live.')
                    self._hosts_deaduntil[:] = [0] * len(self._hosts_deaduntil)
        finally:
            super(MemcacheClientPool, self).release(conn)
