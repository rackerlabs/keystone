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

import uuid

import six

from keystone.assignment import schema as assignment_schema
from keystone.catalog import schema as catalog_schema
from keystone.common import validation
from keystone.common.validation import parameter_types
from keystone.common.validation import validators
from keystone.credential import schema as credential_schema
from keystone import exception
from keystone.federation import schema as federation_schema
from keystone.identity import schema as identity_schema
from keystone.oauth1 import schema as oauth1_schema
from keystone.policy import schema as policy_schema
from keystone.resource import schema as resource_schema
from keystone.tests import unit
from keystone.trust import schema as trust_schema

class UserValidationTestCase(unit.BaseTestCase):
    """Test for V2 User API Validation"""

    def setUp(self):
        super(UserValidationTestCase, self).setUp()

        schema = identity_schema.user_create
        self.user_validator = validators.SchemaValidator(schema)

    def test_validate_create_user_succeeds(self):
        request = {
            'enabled': True,
            'name': 'bob'
        }
        self.user_validator.validate(request)

    def test_validate_create_user_fails_with_invalid_params(self):
        request = {
            'client': 'shakalaka'
        }
        self.assertRaises(exception.SchemaValidationError,
                          self.user_validator.validate,
                          request)

    def test_validate_create_user_fails_with_no_params(self):
        request = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.user_validator.validate,
                          request)

    def test_validate_create_user_fails_with_invalid_name(self):
        request = {
            'enabled': True,
            'name': 42
        }
        self.assertRaises(exception.SchemaValidationError,
                          self.user_validator.validate,
                          request)
