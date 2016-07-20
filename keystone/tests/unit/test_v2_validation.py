# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from keystone.common.validation import validators
from keystone import exception
from keystone.identity import schema as identity_schema
from keystone.tests import unit


class UserValidationTestCase(unit.BaseTestCase):
    """Test for V2 User API Validation."""

    def setUp(self):
        super(UserValidationTestCase, self).setUp()

        schema_user_create = identity_schema.user_create_v2
        schema_user_update = identity_schema.user_update_v2
        self.create_validator = validators.SchemaValidator(schema_user_create)
        self.update_validator = validators.SchemaValidator(schema_user_update)

    def test_validate_user_create_succeeds(self):
        request = {
            'name': 'bob'
        }
        self.create_validator.validate(request)

    def test_validate_user_create_fails_with_invalid_params(self):
        request = {
            'client': 'shakalaka'
        }
        self.assertRaises(exception.SchemaValidationError,
                          self.create_validator.validate,
                          request)

    def test_validate_user_create_fails_with_no_params(self):
        request = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_validator.validate,
                          request)

    def test_validate_user_create_fails_with_invalid_name(self):
        request = {
            'name': 42
        }
        self.assertRaises(exception.SchemaValidationError,
                          self.create_validator.validate,
                          request)

    def test_validate_user_update_succeeds(self):
        request = {
            'enabled': True
        }
        self.update_validator.validate(request)

    def test_validate_user_update_succeeds_with_no_params(self):
        request = {}
        self.update_validator.validate(request)

    def test_validate_user_update_fails_with_invalid_params(self):
        request = {
            'enabled': 'maybe'
        }
        self.assertRaises(exception.SchemaValidationError,
                          self.update_validator.validate,
                          request)
