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

from keystone.common import utils
from keystone import tests


class TestPasswordHashing(tests.BaseTestCase):

    def setUp(self):
        super(TestPasswordHashing, self).setUp()
        self.password = uuid.uuid4().hex
        self.hashed_password = utils.hash_password(self.password)

    def test_that_we_can_verify_a_password_against_a_hash(self):
        self.assertTrue(utils.check_password(self.password,
                                             self.hashed_password))

    def test_that_an_incorrect_password_fails_to_validate(self):
        bad_password = uuid.uuid4().hex
        self.assertFalse(utils.check_password(bad_password,
                                              self.hashed_password))

    def test_that_a_hash_can_not_be_validated_against_a_hash(self):
        # NOTE(dstanek): Bug 1279849 reported a problem where passwords
        # were not being hashed if they already looked like a hash. This
        # would allow someone to hash their password ahead of time
        # (potentially getting around password requirements, like
        # length) and then they could auth with their original password.
        new_hashed_password = utils.hash_password(self.hashed_password)
        self.assertFalse(utils.check_password(self.password,
                                              new_hashed_password))


class TestIsEmpty(tests.BaseTestCase):

    def setUp(self):
        super(TestIsEmpty, self).setUp()

    def test_None_is_empty(self):
        self.assertTrue(utils.is_empty(None))

    def test_empty_string_is_empty(self):
        self.assertTrue(utils.is_empty(''))

    def test_empty_list_is_empty(self):
        self.assertTrue(utils.is_empty([]))

    def test_empty_dict_is_empty(self):
        self.assertTrue(utils.is_empty({}))

    def test_zero_is_not_empty(self):
        self.assertFalse(utils.is_empty(0))

    def test_False_is_not_empty(self):
        self.assertFalse(utils.is_empty(False))

    def test_string_is_not_empty(self):
        self.assertFalse(utils.is_empty("this is a non-empty string"))

    def test_list_is_not_empty(self):
        self.assertFalse(utils.is_empty(["this is a non-empty list"]))

    def test_dict_is_not_empty(self):
        self.assertFalse(utils.is_empty({"this": "is a non-empty dict"}))
