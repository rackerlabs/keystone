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

import time

import mock
from testtools import matchers

from keystone.common.cache import _memcache_pool
from keystone.tests import core


class _TestConnectionPool(_memcache_pool.ConnectionPool):
    destroyed_value = 'destroyed'

    def _create_connection(self):
        return mock.MagicMock()

    def _destroy_connection(self, conn):
        conn(self.destroyed_value)


class TestConnectionPool(core.TestCase):
    def setUp(self):
        super(TestConnectionPool, self).setUp()
        self.unused_timeout = 10
        self.maxsize = 2
        self.connection_pool = _TestConnectionPool(
            maxsize=self.maxsize,
            unused_timeout=self.unused_timeout)
        self.addCleanup(self.cleanup_instance('connection_pool'))

    def test_get_context_manager(self):
        self.assertThat(self.connection_pool._free_pool, matchers.HasLength(0))
        with self.connection_pool.get() as conn:
            self.assertEqual(1, self.connection_pool._acquired)
        self.assertEqual(0, self.connection_pool._acquired)
        self.assertThat(self.connection_pool._free_pool, matchers.HasLength(1))
        self.assertEqual(conn, self.connection_pool._free_pool[0].connection)

    def test_cleanup_pool(self):
        self.test_get_context_manager()
        newtime = time.time() + self.unused_timeout * 2
        with mock.patch.object(time, 'time', return_value=newtime):
            conn = self.connection_pool._free_pool[0].connection
            self.connection_pool._cleanup_pool()
            conn.assert_has_calls(
                [mock.call(self.connection_pool.destroyed_value)])
        self.assertThat(self.connection_pool._free_pool, matchers.HasLength(0))

    def test_acquire_conn_exception_returns_acquired_count(self):
        class TestException(Exception):
            pass

        def new_create_conn(self):
            raise TestException()

        def get_conn():
            with self.connection_pool.get():
                pass

        with mock.patch.object(_TestConnectionPool, '_create_connection',
                               new_create_conn):
            self.assertRaises(TestException, get_conn)
            self.assertThat(self.connection_pool._free_pool,
                            matchers.HasLength(0))
            self.assertEqual(0, self.connection_pool._acquired)
