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
from keystone.common.validation import parameter_types
from keystone.common.validation import validators
from keystone import exception
from keystone import tests


# Test schema to validate create requests against
_CREATE = {
    'type': 'object',
    'properties': {
        'name': parameter_types.name,
        'description': parameter_types.description,
        'enabled': parameter_types.boolean,
        'url': parameter_types.url,
        'email': parameter_types.email
    },
    'required': ['name'],
    'additionalProperties': True,
}


_UPDATE = {}


_VALID_ENABLED_FORMATS = [True, 'True', 'TRUE', 'true', '1',
                          False, 'False', 'FALSE', 'false', '0']

_INVALID_ENABLED_FORMATS = ['some string', 1, 0]


class BaseValidationTestCase(tests.TestCase):

    def setUp(self):
        super(BaseValidationTestCase, self).setUp()
        self.resource_name = 'some resource name'
        self.description = 'Some valid description'
        self.valid_enabled = True
        self.valid_url = 'http://example.com'
        self.valid_email = 'joe@example.com'
        # create two validators, one using the _CREATE schema and the other
        # using the _UPDATE schema. These can be used in the test cases
        # according to what is being validated.
        self.create_schema_validator = validators.SchemaValidator(_CREATE)
        self.update_schema_validator = validators.SchemaValidator(_UPDATE)

    def test_create_schema_with_all_valid_parameters(self):
        """Test that we can validate a request with proper parameters."""
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': uuid.uuid4().hex,
                               'description': self.description,
                               'enabled': self.valid_enabled,
                               'url': self.valid_url}
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

    def test_create_schema_with_invalid_url(self):
        invalid_url = 'http//something.com'
        request_to_validate = {'name': self.resource_name,
                               'url': invalid_url}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_valid_email(self):
        request_to_validate = {'name': self.resource_name,
                               'email': self.valid_email}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_email(self):
        request_to_validate = {'name': self.resource_name,
                               'email': 'some invalid email value'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)


class ProjectValidationTestCase(BaseValidationTestCase):
    """Test for V3 Project API validation."""

    def setUp(self):
        super(ProjectValidationTestCase, self).setUp()

        self.project_name = 'My Project'

        create = assignment_schema.project_create
        update = assignment_schema.project_update
        delete = assignment_schema.project_delete
        self.create_project_validator = validators.SchemaValidator(create)
        self.update_project_validator = validators.SchemaValidator(update)
        self.delete_project_validator = validators.SchemaValidator(delete)

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
        request_to_validate = {'domain_id': uuid.uuid4().hex}
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
    """Test for V3 Domain API validation."""

    def setUp(self):
        super(DomainValidationTestCase, self).setUp()

        self.domain_name = 'My Domain'

        create = assignment_schema.domain_create
        update = assignment_schema.domain_update
        self.create_domain_validator = validators.SchemaValidator(create)
        self.update_domain_validator = validators.SchemaValidator(update)

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
        request_to_validate = {'domain_id': uuid.uuid4().hex}
        self.update_schema_validator.validate(request_to_validate)

    def test_validate_domain_update_request_with_no_parameters_fails(self):
        """Test that an exception is raised when updating a domain without
           any parameters.
        """
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_domain_validator.validate,
                          request_to_validate)


class RoleValidationTestCase(BaseValidationTestCase):
    """Test for V3 Role API validation."""

    def setUp(self):
        super(RoleValidationTestCase, self).setUp()

        self.role_name = 'My Role'

        create = assignment_schema.role_create
        update = assignment_schema.role_update
        self.create_role_validator = validators.SchemaValidator(create)
        self.update_role_validator = validators.SchemaValidator(update)

    def test_validate_role_request(self):
        """Test we can successfully validate a create role request."""
        request_to_validate = {'name': self.role_name}
        self.create_role_validator.validate(request_to_validate)

    def test_validate_role_create_without_name_raises_exception(self):
        """Test that we raise an exception when `name` isn't included."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_role_validator.validate,
                          request_to_validate)

    def test_validate_role_create_when_name_is_not_string_fails(self):
        """Test that an exception is raised when creating a role with a `name`
           that isn't a string.
        """
        request_to_validate = {'name': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_role_validator.validate,
                          request_to_validate)
        request_to_validate = {'name': 24}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_role_validator.validate,
                          request_to_validate)

    def test_validate_role_update_request(self):
        """Test that we validate a role update request."""
        request_to_validate = {'name': 'My New Role'}
        self.update_role_validator.validate(request_to_validate)

    def test_validate_role_update_fails_with_invalid_name(self):
        """Test that we raise an exception when validating an update request
           with an invalid `name`.
        """
        request_to_validate = {'name': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_role_validator.validate,
                          request_to_validate)

        request_to_validate = {'name': 24}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_role_validator.validate,
                          request_to_validate)
