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

import uuid

from dogpile.cache import api as dogpile
from dogpile.cache.backends import memory
from oslo_config import fixture as config_fixture

from keystone.common import cache
import keystone.conf
from keystone.tests import unit


CONF = keystone.conf.CONF


class TestCacheRegion(unit.BaseTestCase):

    def setUp(self):
        super(TestCacheRegion, self).setUp()
        self.config_fixture = self.useFixture(config_fixture.Config(CONF))
        self.config_fixture.config(
            # TODO(morganfainberg): Make Cache Testing a separate test case
            # in tempest, and move it out of the base unit tests.
            group='cache',
            backend='dogpile.cache.memory')

        self.region_name = uuid.uuid4().hex
        self.region = cache.create_region('test_region')
        cache.configure_cache(region=self.region)

        # TODO(dstanek): this should be a mock entrypoint
        self.cache_dict = {}
        self.backend = memory.MemoryBackend({'cache_dict': self.cache_dict})
        self.region.backend = self.backend

    def test_region_singular_methods(self):
        key = uuid.uuid4().hex
        value = uuid.uuid4().hex

        # key does not exist
        self.assertIsInstance(self.region.get(key), dogpile.NoValue)
        # make it exist
        self.region.set(key, value)
        # ensure it exists
        self.assertEqual(value, self.region.get(key))

        # test invalidation
        self.region.invalidate()
        self.assertIsInstance(self.region.get(key), dogpile.NoValue)

    def test_memoize_decorator(self):
        memoize = cache.get_memoization_decorator('cache', region=self.region)

        @memoize
        def func(value):
            return value + uuid.uuid4().hex

        key = uuid.uuid4().hex

        # test get/set
        return_value = func(key)
        # the values should be the same since it comes from the cache
        self.assertEqual(return_value, func(key))

        # test invalidation
        self.region.invalidate()
        new_value = func(key)
        self.assertNotEqual(return_value, new_value)
