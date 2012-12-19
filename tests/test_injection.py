# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

import unittest2 as unittest
import uuid

from keystone.common import dependency


class TestDependencyInjection(unittest.TestCase):
    def test_dependency_injection(self):
        class SodaInterface(object):
            def do_work(self):
                assert False

        @dependency.provider('pepsi_api')
        class PepsiImplementation(SodaInterface):
            def do_work(self):
                return True

        @dependency.provider('coke_api')
        class CokeImplementation(SodaInterface):
            def do_work(self):
                return True

        @dependency.requires('coke_api', 'pepsi_api')
        class Consumer(object):
            def do_work_with_dependencies(self):
                assert self.coke_api.do_work()
                assert self.pepsi_api.do_work()

        # initialize dependency providers
        coke_api = CokeImplementation()
        pepsi_api = PepsiImplementation()

        # ... sometime later, initialize a dependency consumer
        consumer = Consumer()

        # the expected dependencies should be available to the consumer
        self.assertIs(consumer.coke_api, coke_api)
        self.assertIs(consumer.pepsi_api, pepsi_api)
        self.assertIsInstance(consumer.coke_api, SodaInterface)
        self.assertIsInstance(consumer.pepsi_api, SodaInterface)
        consumer.do_work_with_dependencies()

    def test_nested_requirements(self):
        class SodaInterface(object):
            def do_work(self):
                assert False

        @dependency.provider('pepsi_api')
        class PepsiImplementation(SodaInterface):
            def do_work(self):
                return True

        @dependency.provider('coke_api')
        class CokeImplementation(SodaInterface):
            def do_work(self):
                return True

        @dependency.requires('pepsi_api')
        class ParentConsumer(object):
            def do_work_with_dependencies(self):
                assert self.pepsi_api.do_work()

        @dependency.requires('coke_api')
        class ChildConsumer(ParentConsumer):
            def do_work_with_dependencies(self):
                assert self.coke_api.do_work()
                super(ChildConsumer, self).do_work_with_dependencies()

        # initialize dependency providers
        coke_api = CokeImplementation()
        pepsi_api = PepsiImplementation()

        consumer = ChildConsumer()

        # the expected dependencies should be available to the consumer
        self.assertIs(consumer.coke_api, coke_api)
        self.assertIs(consumer.pepsi_api, pepsi_api)
        self.assertIsInstance(consumer.coke_api, SodaInterface)
        self.assertIsInstance(consumer.pepsi_api, SodaInterface)
        consumer.do_work_with_dependencies()

    def test_unresolvable_dependency(self):
        @dependency.requires(uuid.uuid4().hex)
        class Consumer(object):
            pass

        with self.assertRaises(dependency.UnresolvableDependencyException):
            Consumer()
