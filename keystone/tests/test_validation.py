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


from keystone.assignment import schema as assignment_schema
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


_VALID_UUID_FORMAT = uuid.uuid4().hex

# Test invalid UUID formats including UUIDs that are too short, too
# long, and contain invalid characters
_INVALID_UUID_FORMATS = ['42b8550cfe474cc8be1e209ccd835d',
                         '42b8550cfe474cc8be1e209ccd835d273',
                         '42b8550cfe474cc8be1e209ccd835dzz',
                         '42b8550cfe474cc8be1e209ccd835d 7',
                         None]

_VALID_ENABLED_FORMATS = [True, 'True', 'TRUE', 'true', '1',
                          False, 'False', 'FALSE', 'false', '0']

_INVALID_ENABLED_FORMATS = ['some string', 1, 0]


class BaseValidationTestCase(tests.TestCase):

    def setUp(self):
        super(BaseValidationTestCase, self).setUp()
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
        """Test that we can validate a request with proper parameters."""
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': self.valid_uuid,
                               'description': self.description,
                               'enabled': self.valid_enabled}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_uuid_formats_raises_exception(self):
        """Test that an exception is raised when using invalide UUID formats
           in requests.
        """
        for invalid_uuid in _INVALID_UUID_FORMATS:
            request_to_validate = {'name': self.resource_name,
                                   'some_uuid': invalid_uuid}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_schema_validator.validate,
                              request_to_validate)

    def test_create_schema_with_valid_uuid_format(self):
        """Test that we validate a request with a proper UUID format."""
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': self.valid_uuid}
        # Make sure validation doensn't raise a validation exception
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_enabled_format_raises_exception(self):
        """Test that we raise an exception when `enabled` isn't a valid
           boolean value.
        """
        invalid_enabled_formats = 'some string'
        request_to_validate = {'name': self.resource_name,
                               'enabled': invalid_enabled_formats}

        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_valid_enabled_formats(self):
        """Test that we can validate `enabled` as boolean-like values."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': valid_enabled}
            # Make sure validation doesn't raise a validation exception
            self.create_schema_validator.validate(request_to_validate)


class ProjectValidationTestCase(BaseValidationTestCase):
    """Test for V3 Project API validation."""

    def setUp(self):
        super(ProjectValidationTestCase, self).setUp()

        self.project_name = 'My Project'

        create = assignment_schema.project_create
        update = assignment_schema.project_update
        delete = assignment_schema.project_delete
        self.create_project_validator = validators._SchemaValidator(create)
        self.update_project_validator = validators._SchemaValidator(update)
        self.delete_project_validator = validators._SchemaValidator(delete)

    def test_validate_project_request(self):
        """Test that we validate a project with `name` in request."""
        request_to_validate = {'name': self.project_name}
        self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_without_name_raises_exception(self):
        """Test that an exception is raised when `name` isn't in the project
           creation request.
        """
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_project_validator.validate,
                          request_to_validate)

    def test_validate_project_request_with_enabled(self):
        """Test that we can validate `enabled` as boolean-like values for
           projects.
        """
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'enabled': valid_enabled}
            # Make sure an exception isn't raised
            self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_with_invalid_enabled_fails(self):
        """Test that an exception is raised when `enabled` isn't a
           boolean-like value.
        """
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_project_validator.validate,
                              request_to_validate)

    def test_validate_project_request_with_valid_domain_id(self):
        """Test that we can validate `domain_id` with a valid UUID format."""
        request_to_validate = {'name': self.project_name,
                               'domain_id': _VALID_UUID_FORMAT}
        self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_with_invalid_uuid_raises_exception(self):
        """Test that we raise an exception when using an invalid UUID formats
           as `domain_id`.
        """
        for invalid_uuid in _INVALID_UUID_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'domain_id': invalid_uuid}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_project_validator.validate,
                              request_to_validate)

    def test_validate_project_request_with_valid_description(self):
        """Test that we validate `description` in create project requests."""
        request_to_validate = {'name': self.project_name,
                               'description': 'My Project'}
        self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_with_invalid_description(self):
        """Test that an exception is raised when validating `description` as a
           non-string value.
        """
        request_to_validate = {'name': self.project_name,
                               'description': False}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_project_validator.validate,
                          request_to_validate)

    def test_validate_project_update_request(self):
        """Test that we validate a project update request."""
        request_to_validate = {'domain_id': _VALID_UUID_FORMAT}
        self.update_schema_validator.validate(request_to_validate)

    def test_validate_project_update_request_with_no_parameters_fails(self):
        """Test that an exception is raised when updating a project without
           any parameters.
        """
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_project_validator.validate,
                          request_to_validate)

    def test_validate_project_delete_request_takes_no_parameters(self):
        """Test the delete validation schema."""
        request_to_validate = {}
        self.delete_project_validator.validate(request_to_validate)

    def test_validate_project_delete_with_parameters_raises_exception(self):
        """Test that an exception is raised when validating a delete request
           that has parameters.
        """
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.delete_project_validator.validate,
                          request_to_validate)


class DomainValidationTestCase(BaseValidationTestCase):
    """Test for V3 Project API validation."""

    def setUp(self):
        super(DomainValidationTestCase, self).setUp()

        self.domain_name = 'My Domain'

        create = assignment_schema.domain_create
        update = assignment_schema.domain_update
        self.create_domain_validator = validators._SchemaValidator(create)
        self.update_domain_validator = validators._SchemaValidator(update)

    def test_validate_domain_request(self):
        """Make sure we successfully validate a create domain request."""
        request_to_validate = {'name': self.domain_name}
        self.create_domain_validator.validate(request_to_validate)

    def test_validate_domain_request_without_name_raises_exception(self):
        """Make sure we raise an exception when `name` isn't included."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_domain_validator.validate,
                          request_to_validate)

    def test_validate_domain_request_with_enabled(self):
        """Test that we can validate `enabled` as boolean-like values for
           domains.
        """
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.domain_name,
                                   'enabled': valid_enabled}
            # Make sure an exception isn't raised
            self.create_domain_validator.validate(request_to_validate)

    def test_validate_domain_request_with_invalid_enabled_fails(self):
        """Test that an exception is raised when `enabled` isn't a
           boolean-like value.
        """
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.domain_name,
                                   'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_domain_validator.validate,
                              request_to_validate)

    def test_validate_domain_request_with_valid_description(self):
        """Test that we validate `description` in create domain requests."""
        request_to_validate = {'name': self.domain_name,
                               'description': 'My Domain'}
        self.create_domain_validator.validate(request_to_validate)

    def test_validate_domain_request_with_invalid_description(self):
        """Test that an exception is raised when validating `description` as a
           non-string value.
        """
        request_to_validate = {'name': self.domain_name,
                               'description': False}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_domain_validator.validate,
                          request_to_validate)

    def test_validate_domain_update_request(self):
        """Test that we validate a domain update request."""
        request_to_validate = {'domain_id': _VALID_UUID_FORMAT}
        self.update_schema_validator.validate(request_to_validate)

    def test_validate_domain_update_request_with_no_parameters_fails(self):
        """Test that an exception is raised when updating a domain without
           any parameters.
        """
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_domain_validator.validate,
                          request_to_validate)
