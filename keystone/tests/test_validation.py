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

from keystone.assignment import schema as assignment_schema
from keystone.catalog import schema as catalog_schema
from keystone.common.validation import parameter_types
from keystone.common.validation import validators
from keystone.credential import schema as credential_schema
from keystone import exception
from keystone.policy import schema as policy_schema
from keystone import tests
from keystone.trust import schema as trust_schema


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


_VALID_ENABLED_FORMATS = [True, False]

_INVALID_ENABLED_FORMATS = ['some string', 1, 0, 'True', 'False']


class BaseValidationTestCase(tests.TestCase):

    def setUp(self):
        super(BaseValidationTestCase, self).setUp()
        self.resource_name = 'some resource name'
        self.description = 'Some valid description'
        self.valid_enabled = True
        self.valid_url = 'http://example.com'
        self.valid_email = 'joe@example.com'
        self.create_schema_validator = validators.SchemaValidator(_CREATE)
        self.update_schema_validator = validators.SchemaValidator(_UPDATE)

    def test_create_schema_with_all_valid_parameters(self):
        """Validate proper values against test schema."""
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': uuid.uuid4().hex,
                               'description': self.description,
                               'enabled': self.valid_enabled,
                               'url': self.valid_url}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_name_too_long_raises_exception(self):
        """Validate long names.

        Validate that an exception is raised when validating a string of 255+
        characters passed in as a name.
        """
        invalid_name = ''
        for i in range(255):
            invalid_name = invalid_name + str(i)

        request_to_validate = {'name': invalid_name}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_name_too_short_raises_exception(self):
        """Validate short names.

        Test that an exception is raised when passing a string of length
        zero as a name parameter.
        """
        request_to_validate = {'name': ''}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_unicode_name_is_successful(self):
        """Test that we successfully validate a unicode string."""
        request_to_validate = {'name': u'αβγδ'}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_enabled_format_raises_exception(self):
        """Validate invalid enabled formats.

        Test that an exception is raised when passing invalid boolean-like
        values as `enabled`.
        """
        invalid_enabled_formats = 'some string'
        request_to_validate = {'name': self.resource_name,
                               'enabled': invalid_enabled_formats}

        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_valid_enabled_formats(self):
        """Validate valid enabled formats.

        Test that we have successful validation on boolean values for
        `enabled`.
        """
        valid_enabled_formats = [True, False]

        for valid_enabled in valid_enabled_formats:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': valid_enabled}
            # Make sure validation doesn't raise a validation exception
            self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_valid_urls(self):
        """Test that proper urls are successfully validated."""
        valid_urls = ['https://169.254.0.1', 'https://example.com',
                      'https://EXAMPLE.com', 'https://127.0.0.1:35357',
                      'https://localhost']

        for valid_url in valid_urls:
            request_to_validate = {'name': self.resource_name,
                                   'url': valid_url}
            self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_urls(self):
        """Test that an exception is raised when validating improper urls."""
        invalid_urls = ['http//something.com',
                        'https//something.com',
                        'https://9.9.9']

        for invalid_url in invalid_urls:
            request_to_validate = {'name': self.resource_name,
                                   'url': invalid_url}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_schema_validator.validate,
                              request_to_validate)

    def test_create_schema_with_valid_email(self):
        """Validate email address

        Test that we successfully validate properly formatted email
        addresses.
        """
        request_to_validate = {'name': self.resource_name,
                               'email': self.valid_email}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_email(self):
        """Validate invalid email address

        Test that an exception is raised when validating improperly
        formatted email addresses.
        """
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

    def test_validate_project_request_without_name_fails(self):
        """Validate project request fails without name."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_project_validator.validate,
                          request_to_validate)

    def test_validate_project_request_with_enabled(self):
        """Validate `enabled` as boolean-like values for projects."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'enabled': valid_enabled}
            self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_with_invalid_enabled_fails(self):
        """Exception is raised when `enabled` isn't a boolean-like value."""
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

    def test_validate_project_request_with_invalid_description_fails(self):
        """Exception is raised when `description` as a non-string value."""
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
        """Exception is raised when updating project without parameters."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_project_validator.validate,
                          request_to_validate)

    def test_validate_project_delete_request_takes_no_parameters(self):
        """Test the delete validation schema."""
        request_to_validate = {}
        self.delete_project_validator.validate(request_to_validate)

    def test_validate_project_delete_with_parameters_fails(self):
        """Exception is raised on validate delete request with parameters."""
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

    def test_validate_domain_request_without_name_fails(self):
        """Make sure we raise an exception when `name` isn't included."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_domain_validator.validate,
                          request_to_validate)

    def test_validate_domain_request_with_enabled(self):
        """Validate `enabled` as boolean-like values for domains."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.domain_name,
                                   'enabled': valid_enabled}
            self.create_domain_validator.validate(request_to_validate)

    def test_validate_domain_request_with_invalid_enabled_fails(self):
        """Exception is raised when `enabled` isn't a boolean-like value."""
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

    def test_validate_domain_request_with_invalid_description_fails(self):
        """Exception is raised when `description` is a non-string value."""
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
        """Exception is raised when updating a domain without parameters."""
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
        """Exception is raised on role create with a non-string `name`."""
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

    def test_validate_role_update_fails_with_invalid_name_fails(self):
        """Exception when validating an update request with invalid `name`."""
        request_to_validate = {'name': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_role_validator.validate,
                          request_to_validate)

        request_to_validate = {'name': 24}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_role_validator.validate,
                          request_to_validate)


class RegionValidationTestCase(BaseValidationTestCase):
    """Test for V3 Region API validation."""

    def setUp(self):
        super(RegionValidationTestCase, self).setUp()

        self.region_name = 'My Region'

        create = catalog_schema.region_create
        update = catalog_schema.region_update
        self.create_region_validator = validators.SchemaValidator(create)
        self.update_region_validator = validators.SchemaValidator(update)

    def test_validate_region_request(self):
        """Test that we validate a basic region request."""
        # Create_region doesn't take any parameters in the request so let's
        # make sure we cover that case.
        request_to_validate = {}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_create_request_with_parameters(self):
        """Test that we validate a region request with parameters."""
        request_to_validate = {'id': 'us-east',
                               'description': 'US East Region',
                               'parent_region_id': 'US Region'}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_create_with_uuid(self):
        """Test that we validate a region request with a UUID as the id."""
        request_to_validate = {'id': uuid.uuid4().hex,
                               'description': 'US East Region',
                               'parent_region_id': uuid.uuid4().hex}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_create_succeeds_with_extra_parameters(self):
        """Validate create region request with extra values."""
        request_to_validate = {'other_attr': uuid.uuid4().hex}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_update_succeeds(self):
        """Test that we validate a region update request."""
        request_to_validate = {'id': 'us-west',
                               'description': 'US West Region',
                               'parent_region_id': 'us-region'}
        self.update_region_validator.validate(request_to_validate)

    def test_validate_region_update_succeeds_with_extra_parameters(self):
        """Validate extra attributes in the region update request."""
        request_to_validate = {'other_attr': uuid.uuid4().hex}
        self.update_region_validator.validate(request_to_validate)

    def test_validate_region_update_fails_with_no_parameters(self):
        """Exception raised when passing no parameters in a region update."""
        # An update request should consist of at least one value to update
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_region_validator.validate,
                          request_to_validate)


class ServiceValidationTestCase(BaseValidationTestCase):
    """Test for V3 Service API validation."""

    def setUp(self):
        super(ServiceValidationTestCase, self).setUp()

        create = catalog_schema.service_create
        update = catalog_schema.service_update
        self.create_service_validator = validators.SchemaValidator(create)
        self.update_service_validator = validators.SchemaValidator(update)

    def test_validate_service_create_succeeds(self):
        """Test that we validate a service create request."""
        request_to_validate = {'name': 'Nova',
                               'description': 'OpenStack Compute Service',
                               'enabled': True,
                               'type': 'compute'}
        self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_succeeds_with_required_parameters(self):
        """Validate a service create request with the required parameters."""
        # The only parameter type required for service creation is 'type'
        request_to_validate = {'type': 'compute'}
        self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_fails_without_type(self):
        """Exception raised when trying to create a service without `type`."""
        request_to_validate = {'name': 'Nova'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_service_validator.validate,
                          request_to_validate)

    def test_validate_service_create_succeeds_with_extra_parameters(self):
        """Test that extra parameters pass validation on create service."""
        request_to_validate = {'other_attr': uuid.uuid4().hex,
                               'type': uuid.uuid4().hex}
        self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_succeeds_with_valid_enabled(self):
        """Validate boolean values as `enabled`values on service create."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': valid_enabled,
                                   'type': uuid.uuid4().hex}
            self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_fails_with_invalid_enabled(self):
        """Exception raised when boolean-like parameters as `enabled`

        On service create, make sure an exception is raised if `enabled` is
        not a boolean value.
        """
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': invalid_enabled,
                                   'type': uuid.uuid4().hex}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_service_validator.validate,
                              request_to_validate)

    def test_validate_service_update_request_succeeds(self):
        """Test that we validate a service update request."""
        request_to_validate = {'name': 'Cinder',
                               'type': 'volume',
                               'description': 'OpenStack Block Storage',
                               'enabled': False}
        self.update_service_validator.validate(request_to_validate)

    def test_validate_service_update_fails_with_no_parameters(self):
        """Exception raised when updating a service without values."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_service_validator.validate,
                          request_to_validate)

    def test_validate_service_update_succeeds_with_extra_parameters(self):
        """Validateupdating a service with extra parameters."""
        request_to_validate = {'other_attr': uuid.uuid4().hex}
        self.update_service_validator.validate(request_to_validate)

    def test_validate_service_update_succeeds_with_valid_enabled(self):
        """Validate boolean formats as `enabled` on service update."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': valid_enabled}
            self.update_service_validator.validate(request_to_validate)

    def test_validate_service_update_fails_with_invalid_enabled(self):
        """Exception raised when boolean-like values as `enabled`."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.update_service_validator.validate,
                              request_to_validate)


class EndpointValidationTestCase(BaseValidationTestCase):
    """Test for V3 Endpoint API validation."""

    def setUp(self):
        super(EndpointValidationTestCase, self).setUp()

        create = catalog_schema.endpoint_create
        update = catalog_schema.endpoint_update
        self.create_endpoint_validator = validators.SchemaValidator(create)
        self.update_endpoint_validator = validators.SchemaValidator(update)

    def test_validate_endpoint_request_succeeds(self):
        """Test that we validate an endpoint request."""
        request_to_validate = {'enabled': True,
                               'interface': 'admin',
                               'region_id': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_create_succeeds_with_required_parameters(self):
        """Validate an endpoint request with only the required parameters."""
        # According to the Identity V3 API endpoint creation requires
        # 'service_id', 'interface', and 'url'
        request_to_validate = {'service_id': uuid.uuid4().hex,
                               'interface': 'public',
                               'url': 'https://service.example.com:5000/'}
        self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_create_succeeds_with_valid_enabled(self):
        """Validate an endpoint with boolean values.

        Validate boolean values as `enabled` in endpoint create requests.
        """
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enable': valid_enabled,
                                   'service_id': uuid.uuid4().hex,
                                   'interface': 'public',
                                   'url': 'https://service.example.com:5000/'}
            self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_create_endpoint_fails_with_invalid_enabled(self):
        """Exception raised when boolean-like values as `enabled`."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enable': invalid_enabled,
                                   'service_id': uuid.uuid4().hex,
                                   'interface': 'public',
                                   'url': 'https://service.example.com:5000/'}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_endpoint_validator.validate,
                              request_to_validate)

    def test_validate_endpoint_create_succeeds_with_extra_parameters(self):
        """Test that extra parameters pass validation on create endpoint."""
        request_to_validate = {'other_attr': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'interface': 'public',
                               'url': 'https://service.example.com:5000/'}
        self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_create_fails_without_service_id(self):
        """Exception raised when `service_id` isn't in endpoint request."""
        request_to_validate = {'interface': 'public',
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_create_fails_without_interface(self):
        """Exception raised when `interface` isn't in endpoint request."""
        request_to_validate = {'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_create_fails_without_url(self):
        """Exception raised when `url` isn't in endpoint request."""
        request_to_validate = {'service_id': uuid.uuid4().hex,
                               'interface': 'public'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_create_fails_with_invalid_interface(self):
        """Exception raised with invalid `interface`."""
        request_to_validate = {'interface': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_update_fails_with_invalid_enabled(self):
        """Exception raised when `enabled` is boolean-like value."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.update_endpoint_validator.validate,
                              request_to_validate)

    def test_validate_endpoint_update_succeeds_with_valid_enabled(self):
        """Validate `enabled` as boolean values."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': valid_enabled}
            self.update_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_update_fails_with_invalid_interface(self):
        """Exception raised when invalid `interface` on endpoint update."""
        request_to_validate = {'interface': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_update_request_succeeds(self):
        """Test that we validate an endpoint update request."""
        request_to_validate = {'enabled': True,
                               'interface': 'admin',
                               'region_id': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.update_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_update_fails_with_no_parameters(self):
        """Exception raised when no parameters on endpoint update."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_update_succeeds_with_extra_parameters(self):
        """Test that extra parameters pass validation on update endpoint."""
        request_to_validate = {'enabled': True,
                               'interface': 'admin',
                               'region_id': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/',
                               'other_attr': uuid.uuid4().hex}
        self.update_endpoint_validator.validate(request_to_validate)


class CredentialValidationTestCase(BaseValidationTestCase):
    """Test for V3 Credential API validation."""

    def setUp(self):
        super(CredentialValidationTestCase, self).setUp()

        create = credential_schema.credential_create
        update = credential_schema.credential_update
        self.create_credential_validator = validators.SchemaValidator(create)
        self.update_credential_validator = validators.SchemaValidator(update)

    def test_validate_credential_succeeds(self):
        """Test that we validate a credential request."""
        request_to_validate = {'blob': 'some string',
                               'project_id': uuid.uuid4().hex,
                               'type': 'ec2',
                               'user_id': uuid.uuid4().hex}
        self.create_credential_validator.validate(request_to_validate)

    def test_validate_credential_without_blob_fails(self):
        """Exception raised without `blob` in create request."""
        request_to_validate = {'type': 'ec2',
                               'user_id': uuid.uuid4().hex}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_credential_validator.validate,
                          request_to_validate)

    def test_validate_credential_without_user_id_fails(self):
        """Exception raised without `user_id` in create request."""
        request_to_validate = {'blob': 'some credential blob',
                               'type': 'ec2'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_credential_validator.validate,
                          request_to_validate)

    def test_validate_credential_without_type_fails(self):
        """Exception raised without `type` in create request."""
        request_to_validate = {'blob': 'some credential blob',
                               'user_id': uuid.uuid4().hex}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_credential_validator.validate,
                          request_to_validate)

    def test_validate_credential_with_types_succeeds(self):
        """Test that credential type works for ec2 and cert."""
        cred_types = ['ec2', 'cert']

        for c_type in cred_types:
            request_to_validate = {'blob': 'some blob',
                                   'type': c_type,
                                   'user_id': uuid.uuid4().hex}
            # Make sure an exception isn't raised
            self.create_credential_validator.validate(request_to_validate)

    def test_validate_credential_invalid_type_fails(self):
        """Test that `type` only accepts ec2 and cert."""
        invalid_types = ['invalid cert type', False, 2]

        for c_type in invalid_types:
            request_to_validate = {'blob': 'some blob',
                                   'type': c_type,
                                   'user_id': uuid.uuid4().hex}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_credential_validator.validate,
                              request_to_validate)

    def test_validate_credential_with_extra_parameters_succeeds(self):
        """Validate create request with extra parameters."""
        request_to_validate = {'blob': 'some string',
                               'extra': False,
                               'project_id': uuid.uuid4().hex,
                               'type': 'ec2',
                               'user_id': uuid.uuid4().hex}
        self.create_credential_validator.validate(request_to_validate)

    def test_validate_credential_update_succeeds(self):
        """Test that a credential request is properly validated."""
        request_to_validate = {'blob': 'some string',
                               'project_id': uuid.uuid4().hex,
                               'type': 'ec2',
                               'user_id': uuid.uuid4().hex}
        self.update_credential_validator.validate(request_to_validate)

    def test_validate_credential_update_without_parameters_fails(self):
        """Exception is raised on update without parameters."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_credential_validator.validate,
                          request_to_validate)

    def test_validate_credential_update_with_extra_parameters_succeeds(self):
        """Validate credential update with extra parameters."""
        request_to_validate = {'blob': 'some string',
                               'extra': False,
                               'project_id': uuid.uuid4().hex,
                               'type': 'ec2',
                               'user_id': uuid.uuid4().hex}
        self.update_credential_validator.validate(request_to_validate)


class PolicyValidationTestCase(BaseValidationTestCase):
    """Test for V3 Policy API validation."""

    def setUp(self):
        super(PolicyValidationTestCase, self).setUp()

        create = policy_schema.policy_create
        update = policy_schema.policy_update
        self.create_policy_validator = validators.SchemaValidator(create)
        self.update_policy_validator = validators.SchemaValidator(update)

    def test_validate_policy_succeeds(self):
        """Test that we validate a create policy request."""
        request_to_validate = {'blob': 'some blob information',
                               'type': 'application/json'}
        self.create_policy_validator.validate(request_to_validate)

    def test_validate_policy_without_blob_fails(self):
        """Exception raised without `blob` in request."""
        request_to_validate = {'type': 'application/json'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_policy_validator.validate,
                          request_to_validate)

    def test_validate_policy_without_type_fails(self):
        """Exception raised withput `type` in request."""
        request_to_validate = {'blob': 'some blob information'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_policy_validator.validate,
                          request_to_validate)

    def test_validate_policy_create_with_extra_parameters_succeeds(self):
        """Validate policy create with extra parameters."""
        request_to_validate = {'blob': 'some blob information',
                               'type': 'application/json',
                               'extra': 'some extra stuff'}
        self.create_policy_validator.validate(request_to_validate)

    def test_validate_policy_create_with_invalid_type_fails(self):
        """Exception raised when `blob` and `type` are boolean."""
        for prop in ['blob', 'type']:
            request_to_validate = {prop: False}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_policy_validator.validate,
                              request_to_validate)

    def test_validate_policy_update_without_parameters_fails(self):
        """Exception raised when updating policy without parameters."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_policy_validator.validate,
                          request_to_validate)

    def test_validate_policy_update_with_extra_parameters_succeeds(self):
        """Validate policy update request with extra parameters."""
        request_to_validate = {'blob': 'some blob information',
                               'type': 'application/json',
                               'extra': 'some extra stuff'}
        self.update_policy_validator.validate(request_to_validate)

    def test_validate_policy_update_succeeds(self):
        """Test that we validate a policy update request."""
        request_to_validate = {'blob': 'some blob information',
                               'type': 'application/json'}
        self.update_policy_validator.validate(request_to_validate)

    def test_validate_policy_update_with_invalid_type_fails(self):
        """Exception raised when invalid `type` on policy update."""
        for prop in ['blob', 'type']:
            request_to_validate = {prop: False}
            self.assertRaises(exception.SchemaValidationError,
                              self.update_policy_validator.validate,
                              request_to_validate)


class TrustValidationTestCase(BaseValidationTestCase):
    """Test for V3 Trust API validation."""

    def setUp(self):
        super(TrustValidationTestCase, self).setUp()

        create = trust_schema.trust_create
        self.create_trust_validator = validators.SchemaValidator(create)

    def test_validate_trust_succeeds(self):
        """That that we can validate a trust request."""
        request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                               'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': False}
        self.create_trust_validator.validate(request_to_validate)

    def test_validate_trust_with_all_parameters_succeeds(self):
        """Test that we can validate a trust request with all parameters."""
        request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                               'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': False,
                               'project_id': uuid.uuid4().hex,
                               'roles': [uuid.uuid4().hex, uuid.uuid4().hex],
                               'expires_at': 'some timestamp',
                               'remaining_uses': 2}
        self.create_trust_validator.validate(request_to_validate)

    def test_validate_trust_without_trustor_id_fails(self):
        """Test that an exception is raised when validating a trust request
           that doesn't have `trustor_user_id` in the request.
        """
        request_to_validate = {'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': False}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_trust_validator.validate,
                          request_to_validate)

    def test_validate_trust_without_trustee_id_fails(self):
        """Test that an exception is raised when validating a trust request
           that doesn't have `trustee_user_id` in the request.
        """
        request_to_validate = {'trusor_user_id': uuid.uuid4().hex,
                               'impersonation': False}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_trust_validator.validate,
                          request_to_validate)

    def test_validate_trust_without_impersonation_fails(self):
        """Test that an exception is raised when validating a trust request
           that doesn't have `impersonation` in the request.
        """
        request_to_validate = {'trustee_user_id': uuid.uuid4().hex,
                               'trustor_user_id': uuid.uuid4().hex}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_trust_validator.validate,
                          request_to_validate)

    def test_validate_trust_with_extra_parameters_succeeds(self):
        """Test that we can validate a trust request with extra parameters."""
        request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                               'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': False,
                               'project_id': uuid.uuid4().hex,
                               'roles': [uuid.uuid4().hex, uuid.uuid4().hex],
                               'expires_at': 'some timestamp',
                               'remaining_uses': 2,
                               'extra': 'something extra!'}
        self.create_trust_validator.validate(request_to_validate)

    def test_validate_trust_with_invalid_impersonation_fails(self):
        """Test that an exception is raised when validating a trust with an
           invalid `impersonation` value.
        """
        request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                               'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': 2}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_trust_validator.validate,
                          request_to_validate)

    def test_validate_trust_with_null_remaining_uses_succeeds(self):
        """Test that we can validate a trust request that has None as a value
           for `remaining_uses`.
        """
        request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                               'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': False,
                               'remaining_uses': None}
        self.create_trust_validator.validate(request_to_validate)

    def test_validate_trust_with_remaining_uses_succeeds(self):
        """Test that we can validate a trust request that has integer as a
           value for `remaining_uses`.
        """
        request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                               'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': False,
                               'remaining_uses': 2}
        self.create_trust_validator.validate(request_to_validate)

    def test_validate_trust_with_invalid_expires_at_fails(self):
        """Test that an exception is raised when an invalid type is passed as
           `expires_at`.
        """
        request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                               'trustee_user_id': uuid.uuid4().hex,
                               'impersonation': False,
                               'expires_at': 3}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_trust_validator.validate,
                          request_to_validate)

    def test_validate_trust_with_role_types_succeeds(self):
        """Test that we can validate a trust request with different role types
           in the request.
        """
        for role in ['member', uuid.uuid4().hex]:
            request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                                   'trustee_user_id': uuid.uuid4().hex,
                                   'impersonation': False,
                                   'roles': {'name': role}}
            self.create_trust_validator.validate(request_to_validate)

    def test_validate_trust_with_invalid_role_type_fails(self):
        """Test that an exception is raised when validating a trust request
           with an invalid role type.
        """
        for role in [False, True, 123, None]:
            request_to_validate = {'trustor_user_id': uuid.uuid4().hex,
                                   'trustee_user_id': uuid.uuid4().hex,
                                   'impersonation': False,
                                   'roles': role}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_trust_validator.validate,
                              request_to_validate)
