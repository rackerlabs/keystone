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


from keystone import exception
from keystone import tests
from keystone.validation import common_parameter_types
from keystone.validation import validators


# Test schema to validate create requests against
_CREATE = {
    'type': 'object',
    'properties': {
        'name': common_parameter_types.name,
        'some_uuid': common_parameter_types.uuid,
        'description': common_parameter_types.description,
        'enabled': common_parameter_types.boolean
    },
    'required': ['name'],
    'additionalProperties': True,
}


_UPDATE = {}


class ValidationTestCase(tests.TestCase):

    def setUp(self):
        super(ValidationTestCase, self).setUp()
        self.resource_name = 'some resource name'
        self.valid_uuid = uuid.uuid4().hex
        self.description = 'Some valid description'
        self.valid_enabled = True
        # create two validators, one using the _CREATE schema and the other
        # using the _UPDATE schema. These can be used in the test cases
        # according to what is being validated.
        self.create_schema_validator = validators._SchemaValidator(_CREATE)
        self.update_schema_validator = validators._SchemaValidator(_UPDATE)

    def test_create_schema_with_all_valid_parameters(self):
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': self.valid_uuid,
                               'description': self.description,
                               'enabled': self.valid_enabled}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_uuid_formats_raises_exception(self):
        # Test invalid UUID formats including UUIDs that are too short, too
        # long, and contain invalid characters
        invalid_uuid_formats = ['42b8550cfe474cc8be1e209ccd835d',
                                '42b8550cfe474cc8be1e209ccd835d273',
                                '42b8550cfe474cc8be1e209ccd835dzz',
                                '42b8550cfe474cc8be1e209ccd835d 7',
                                None]
        for invalid_uuid in invalid_uuid_formats:
            request_to_validate = {'name': self.resource_name,
                                   'some_uuid': invalid_uuid}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_schema_validator.validate,
                              request_to_validate)

    def test_create_schema_with_valid_uuid_format(self):
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': self.valid_uuid}
        # Make sure validation doensn't raise a validation exception
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_enabled_format_raises_exception(self):
        invalid_enabled_formats = 'some string'
        request_to_validate = {'name': self.resource_name,
                               'enabled': invalid_enabled_formats}

        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_valid_true_enabled_formats(self):
        valid_enabled_formats = [True, 'True', 'TRUE', 'true', '1']

        for valid_enabled in valid_enabled_formats:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': valid_enabled}
            # Make sure validation doesn't raise a validation exception
            self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_valid_false_enabled_formats(self):
        valid_enabled_formats = [False, 'False', 'FALSE', 'false', '0']

        for valid_enabled in valid_enabled_formats:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': valid_enabled}
            # Make sure an exception isn't raised
            self.create_schema_validator.validate(request_to_validate)
