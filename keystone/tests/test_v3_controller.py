# Copyright 2014 CERN.
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
    """Tests for the V3Controller class."""
    def setUp(self):
        super(V3ControllerTestCase, self).setUp()

        class ControllerUnderTest(controller.V3Controller):
            _mutable_parameters = frozenset(['hello', 'world'])

        self.api = ControllerUnderTest()

    def test_check_immutable_params(self):
        """Pass valid parameters to the method and expect no failure."""
        ref = {
            'hello': uuid.uuid4().hex,
            'world': uuid.uuid4().hex
        }
        self.api.check_immutable_params(ref)

    def test_check_immutable_params_fail(self):
        """Pass invalid parameter to the method and expect failure."""
        ref = dict([(uuid.uuid4().hex, uuid.uuid4().hex) for _ in range(3)])

        ref_msg = ("Could not change immutable attribute(s) "
                   "'%(attributes)s' in target %(target)s")

        ref_msg = ref_msg % {'attributes': ', '.join(ref.keys()),
                             'target': self.api.__class__.__name__}
        exception_msg = None
        try:
            self.api.check_immutable_params(ref)
        except exception.ImmutableAttributeError as e:
            exception_msg = unicode(e)
        else:
            fail_reason = ("%s not raised" %
                           exception.ImmutableAttributeError.__name__)
            self.failureException(fail_reason)

        self.assertEqual(exception_msg, ref_msg)
