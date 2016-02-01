# encoding: utf-8
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

from keystone import compat
from keystone import exception
from keystone.tests import unit


class V2Controller(compat._AllMethodsForbiddenControllerV2):
    def defined_method(self):
        pass


class V3Controller(compat._AllMethodsForbiddenControllerV2):
    def defined_method(self):
        pass


class Test403ForbiddenControllers(unit.BaseTestCase):
    def test_v2_controller(self):
        # Controller should raise 403 for any method not defined on the
        # controller or subclass.
        controller = V2Controller()
        controller.defined_method()
        self.assertRaises(exception.Forbidden, getattr, controller,
                          uuid.uuid4().hex)

    def test_v3_controller(self):
        # Controller should raise 403 for any method not defined on the
        # controller or subclass.
        controller = V3Controller()
        controller.defined_method()
        self.assertRaises(exception.Forbidden, getattr, controller,
                          uuid.uuid4().hex)
