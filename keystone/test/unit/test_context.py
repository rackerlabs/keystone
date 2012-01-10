# Copyright (c) 2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
import unittest2 as unittest
from keystone.frontends import context

_alpha_list = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
random.shuffle(_alpha_list)
DUMMY_TOKEN = "".join(_alpha_list)


class MockWsgiApp(object):
    def __init__(self):
        pass

    def __call__(self, env, start_response):
        pass


def _start_response():
    pass


class ContextTest(unittest.TestCase):
    def setUp(self):
        self.filter = context.ContextFilter(MockWsgiApp(), {})

    def test_context_creation(self):
        env = {'HTTP_X_AUTH_TOKEN': DUMMY_TOKEN}
        self.filter(env, _start_response)
        ctx = env.get("context")
        self.assertTrue(isinstance(ctx, context.RequestContext))
        self.assertEqual(ctx.token_id, DUMMY_TOKEN)


if __name__ == '__main__':
    unittest.main()
