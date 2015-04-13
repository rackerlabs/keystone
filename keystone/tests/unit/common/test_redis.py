# Copyright 2015 Mirantis Inc
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

from keystone.common.cache import core as cache_core
from keystone.tests.unit import core


class TestRedis(core.TestCase):

    FAKE_PATH = '/dev/null'

    def config_overrides(self):
        self.config_fixture.config(
            group='cache',
            backend='keystone.cache.redis',
            redis_url='unix://' + self.FAKE_PATH)

    def setUp(self):
        # self.backend = ks_redis.RedisBackend({})
        super(TestRedis, self).setUp()

    def test_config_assembled(self):
        client = cache_core.REGION.backend.client
        self.assertEqual(
            self.FAKE_PATH,
            client.connection_pool.connection_kwargs['path'])
