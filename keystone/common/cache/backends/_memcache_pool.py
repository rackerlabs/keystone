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

import contextlib
import functools
import itertools
import logging
import threading
import time
import weakref

import memcache

LOG = logging.getLogger(__name__)


def _debug(pool_id, msg, *args, **kwargs):
    thread_id = threading.current_thread().ident
    prefix = 'Memcached pool %s, thread %s: ' % (pool_id, thread_id)
    LOG.debug(prefix + msg, *args, **kwargs)


class ConnectionPool(object):
    def __init__(self, maxsize, unused_timeout, debug=False):
        self._maxsize = maxsize
        self._unused_timeout = unused_timeout
        if debug:
            self._debug = functools.partial(_debug, id(self))
        else:
            self._debug = lambda *_: None
        self._acquired = 0
        self._free_pool = []
        no_free_cond = self._no_free = threading.Condition()
        stop_event = threading.Event()

        def stop(ref):
            stop_event.set()
            # Notify cleaner thread if its waiting on empty pool
            with no_free_cond:
                no_free_cond.notify_all()
        self._ref = weakref.ref(self, stop)

        cleaner_thread = threading.Thread(
            target=self._cleaner,
            args=(self._free_pool, stop_event, no_free_cond, self._debug),
        )
        cleaner_thread.daemon = True
        cleaner_thread.start()

    def _create_connection(self):
        raise NotImplementedError

    # Need this to be available without reference to self to call it from
    # cleaner thread
    @classmethod
    def _destroy_connection(cls, conn):
        raise NotImplementedError

    def acquire(self):
        with self._no_free:
            self._debug('Acquiring connection')
            # Wait for either free connection or free space for a new one
            while not self._free_pool and self._acquired >= self._maxsize:
                self._no_free.wait()
            try:
                # Hope there's a free one
                _, conn = self._free_pool.pop()
            except IndexError:
                # Create a new one
                conn = self._create_connection()
                self._debug('Created a new connection %s', id(conn))
            self._acquired += 1
            self._debug('Acquired connection %s', id(conn))
            return conn

    def release(self, conn):
        with self._no_free:
            self._debug('Releasing connection %s', id(conn))
            # Return connection to pool
            self._free_pool.append((time.time() + self._unused_timeout, conn))
            self._acquired -= 1
            # Notify waiting getters and cleaner
            self._no_free.notify_all()

    @contextlib.contextmanager
    def get(self):
        conn = self.acquire()
        try:
            yield conn
        finally:
            self.release(conn)

    @classmethod
    def _cleaner(cls, free_pool, stop_event, no_free_cond, debug):
        def get_wakeup_time():
            with no_free_cond:
                # If pool is empty, wait for new connection there
                while not free_pool and not stop_event.is_set():
                    no_free_cond.wait()
                # We have at least until timeout of the bottom conn to sleep
                if not stop_event.is_set():
                    return free_pool[0][0]
                else:
                    if not free_pool:
                        return  # We're being stopped and the pool is empty
                    else:
                        return 0  # Don't sleep, just kill'em all

        def get_connections_to_close():
            with no_free_cond:
                # If we're stopping we need to close all connections
                if not stop_event.is_set():
                    now = time.time()
                    # Find first connection that hasn't timed out yet
                    for i, (timeout, conn) in enumerate(free_pool):
                        if timeout >= now:
                            to_close = free_pool[:i]
                            free_pool[:i] = []
                            return to_close
                # We are closing or didn't find not timed out connection,
                # so we need to close all connections (if there are any)
                to_close = free_pool[:]
                free_pool[:] = []
                return to_close

        debug('Cleaner: Started')
        # We'll exit when stop_event is fired and the pool is empty
        while True:
            debug('Cleaner: Getting wakeup time')
            sleep_until = get_wakeup_time()
            if sleep_until is None:
                debug('Cleaner: Stopping')
                break
            now = time.time()
            if now < sleep_until:
                sleep_for = sleep_until - now
                debug('Cleaner: Sleeping for %.1fs', sleep_for)
                stop_event.wait(sleep_for)
            to_close = get_connections_to_close()
            for _, conn in to_close:
                cls._destroy_connection(conn)
                debug('Cleaner: Destroyed connection %s', id(conn))
            del to_close


class DumbPool(ConnectionPool):
    def __init__(self, *args, **kwargs):
        super(DumbPool, self).__init__(*args, **kwargs)
        self._count = itertools.count()

    def _create_connection(self):
        return next(self._count)

    @classmethod
    def _destroy_connection(cls, conn):
        pass

# This 'class' is taken from http://stackoverflow.com/a/22520633/238308
# Don't inherit client from threading.local so that we can reuse clients in
# different threads
MemcacheClient = type('MemcacheClient', (object,),
                      dict(memcache.Client.__dict__))


class MemcacheClientPool(ConnectionPool):
    def __init__(self, url, arguments, **kwargs):
        super(MemcacheClientPool, self).__init__(**kwargs)
        self.url = url
        self.arguments = arguments
        self._hosts_deaduntil = [0] * len(url)

    def _create_connection(self):
        return MemcacheClient(self.url, **self.arguments)

    @classmethod
    def _destroy_connection(cls, conn):
        conn.disconnect_all()

    def acquire(self):
        conn = super(MemcacheClientPool, self).acquire()
        try:
            with self._no_free:
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
            with self._no_free:
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
                            self._debug('Marked host %s dead until %s',
                                        self.url[i], host.deaduntil)
                        else:
                            self._hosts_deaduntil[i] = 0
                # If all hosts are dead we should forget that they're dead.
                # This way we won't get completely shut off until dead_retry
                # seconds pass, but will be checking servers as frequent as we
                # can (over way smaller socket_timeout)
                if all(deaduntil > now for deaduntil in self._hosts_deaduntil):
                    self._debug('All hosts are dead. Marking them as live.')
                    self._hosts_deaduntil[:] = [0] * len(self._hosts_deaduntil)
        finally:
            super(MemcacheClientPool, self).release(conn)
