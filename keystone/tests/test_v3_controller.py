# -*- coding: utf-8 -*-

# Copyright 2014 IBM Corp.
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


import uuid

from keystone.common import controller
from keystone import exception
from keystone import tests


class V3ControllerTestCase(tests.TestCase):
    """Tests for the V3Controller class.

    These tests exercise :class:`keystone.assignment.controllers.Tenant`.

    """
    def setUp(self):
        super(V3ControllerTestCase, self).setUp()
        self.api = controller.V3Controller()
        controller.V3Controller._mutable_parameters = frozenset(
            ['hello', 'world'])

    def test_check_immutabel_params(self):
        """Pass valid parameters to the method and expect no failure.

        """
        ref = {
            'hello': uuid.uuid4().hex,
            'world': uuid.uuid4().hex
        }
        self.api.check_immutable_params(ref)

    def test_check_immutable_params_fail(self):
        """Test whether immutable parameters are correctly catched.

        """
        ref = dict([(uuid.uuid4().hex, uuid.uuid4().hex) for _ in range(3)])
        self.assertRaises(exception.ImmutableAttributeError,
                          self.api.check_immutable_params, ref)
