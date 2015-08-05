# Copyright 2015 Reliance Jio Infocomm Limited
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

import abc

import six

from keystone.common import manager
from keystone import exception
from keystone.tests.unit import core


class TestStableDriverInterface(core.TestCase):

    def test_driver_interface_with_compatibility(self):
        """Tests driver interface with compatibility

        Test that ensures that driver implementation of same version
        as interface is compatible
        """
        def load():
            @six.add_metaclass(manager.CompatibilizerMeta)
            class DriverInterface(object):
                interface_version = 12

            class DriverImplementation(DriverInterface):
                driver_version = 12

        load()

    def test_driver_interface_without_compatibility(self):
        """Tests driver interface without compatibility

        Test that ensures that driver interface won't work with previous
        version of driver implementation if necessary compatibility code is
        not present
        """
        def load():
            @six.add_metaclass(manager.CompatibilizerMeta)
            class DriverInterface(object):
                interface_version = 12

                @abc.abstractmethod
                def method1():
                    pass

                @abc.abstractmethod
                def method2():
                    pass

            class DriverImplementation(DriverInterface):
                driver_version = 11

                def method1():
                    pass

        self.assertRaises(exception.IncompatibleInterface, load)

    def test_driver_interface_with_outdated_implementation(self):
        """Test driver interface with outdated implementation

        Test that ensures that driver implementations of version older than
        the previous version of the interface version aren't supported
        """
        def load():
            @six.add_metaclass(manager.CompatibilizerMeta)
            class DriverInterface(object):
                interface_version = 12

            class DriverImplementation(DriverInterface):
                driver_version = 10

        self.assertRaises(exception.IncompatibleDriver, load)
