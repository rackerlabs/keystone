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

import six

from keystone.common import manager
from keystone import exception
from keystone.tests.unit import core


class TestStableDriverInterface(core.TestCase):

    def test_driver_interface_with_version(self):
        """Tests driver interface with version

        Test that ensures that driver interface with version specified
        works
        """
        def load():
            @six.add_metaclass(manager.CompatibilizerMeta)
            class DriverInterface(object):
                interface_version = 12

            class DriverImplementation(DriverInterface):
                driver_version = 12

        load()

    def test_driver_interface_without_version(self):
        """Tests driver interface without version

        Test that ensures that driver interface without version specified
        fails
        """
        def load():
            @six.add_metaclass(manager.CompatibilizerMeta)
            class DriverInterface(object):
                pass

            class DriverImplementation(DriverInterface):
                driver_version = 12

        self.assertRaises(exception.IncompatibleInterface, load)
