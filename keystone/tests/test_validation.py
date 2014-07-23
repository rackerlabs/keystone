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

import testtools

from keystone.catalog import schema as catalog_schema
from keystone.common import validation
from keystone.common.validation import parameter_types
from keystone.common.validation import validators
from keystone.credential import schema as credential_schema
from keystone import exception
from keystone.policy import schema as policy_schema


# Example model to validate create requests against
#
# class Entity(sql.ModelBase):
#     __tablename__ = 'entity'
#     attributes = ['id', 'name', 'domain_id', 'description']
#     id = sql.Column(sql.String(64), primary_key=True)
#     name = sql.Column(sql.String(255), nullable=False)
#     description = sql.Column(sql.Text(), nullable=True)
#     enabled = sql.Column(sql.Boolean, default=True, nullable=False)
#     url = sql.Column(sql.String(225), nullable=True)
#     email = sql.Column(sql.String(64), nullable=True)

# Test schema to validate create requests against

_entity_properties = {
    'name': parameter_types.name,
    'description': validation.nullable(parameter_types.description),
    'enabled': parameter_types.boolean,
    'url': validation.nullable(parameter_types.url),
    'email': validation.nullable(parameter_types.email)
}

entity_create = {
    'type': 'object',
    'properties': _entity_properties,
    'required': ['name'],
    'additionalProperties': True,
}

entity_update = {
    'type': 'object',
    'properties': _entity_properties,
    'minProperties': 1,
    'additionalProperties': True,
}

_VALID_ENABLED_FORMATS = [True, False]

_INVALID_ENABLED_FORMATS = ['some string', 1, 0, 'True', 'False']


class EntityValidationTestCase(testtools.TestCase):

    def setUp(self):
        super(EntityValidationTestCase, self).setUp()
        self.resource_name = 'some resource name'
        self.description = 'Some valid description'
        self.valid_enabled = True
        self.valid_url = 'http://example.com'
        self.valid_email = 'joe@example.com'
        self.create_schema_validator = validators.SchemaValidator(
            entity_create)
        self.update_schema_validator = validators.SchemaValidator(
            entity_update)

    def test_create_entity_with_all_valid_parameters_succeeds(self):
        """Validate correct for all parameter values against test schema."""
        request_to_validate = {'name': self.resource_name,
                               'description': self.description,
                               'enabled': self.valid_enabled,
                               'url': self.valid_url,
                               'email': self.valid_email}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_entity_with_only_required_valid_parameters_succeeds(self):
        """Validate correct for only parameters values against test schema."""
        request_to_validate = {'name': self.resource_name}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_entity_with_name_too_long_raises_exception(self):
        """Validate long names.

        Validate that an exception is raised when validating a string of 255+
        characters passed in as a name.
        """
        invalid_name = 'a' * 256
        request_to_validate = {'name': invalid_name}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_entity_with_name_too_short_raises_exception(self):
        """Validate short names.

        Test that an exception is raised when passing a string of length
        zero as a name parameter.
        """
        request_to_validate = {'name': ''}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_entity_with_unicode_name_succeeds(self):
        """Test that we successfully validate a unicode string."""
        request_to_validate = {'name': u'αβγδ'}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_entity_with_invalid_enabled_format_raises_exception(self):
        """Validate invalid enabled formats.

        Test that an exception is raised when passing invalid boolean-like
        values as `enabled`.
        """
        for format in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': format}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_schema_validator.validate,
                              request_to_validate)

    def test_create_entity_with_valid_enabled_formats(self):
        """Validate valid enabled formats.

        Test that we have successful validation on boolean values for
        `enabled`.
        """
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': valid_enabled}
            # Make sure validation doesn't raise a validation exception
            self.create_schema_validator.validate(request_to_validate)

    def test_create_entity_with_valid_urls(self):
        """Test that proper urls are successfully validated."""
        valid_urls = ['https://169.254.0.1', 'https://example.com',
                      'https://EXAMPLE.com', 'https://127.0.0.1:35357',
                      'https://localhost']

        for valid_url in valid_urls:
            request_to_validate = {'name': self.resource_name,
                                   'url': valid_url}
            self.create_schema_validator.validate(request_to_validate)

    def test_create_entity_with_invalid_urls(self):
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

    def test_create_entity_with_valid_email(self):
        """Validate email address

        Test that we successfully validate properly formatted email
        addresses.
        """
        request_to_validate = {'name': self.resource_name,
                               'email': self.valid_email}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_entity_with_invalid_email(self):
        """Validate invalid email address.

        Test that an exception is raised when validating improperly
        formatted email addresses.
        """
        request_to_validate = {'name': self.resource_name,
                               'email': 'some invalid email value'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_update_entity_with_no_parameters_fails(self):
        """At least one parameter needs to be present for an update."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_schema_validator.validate,
                          request_to_validate)

    def test_update_entity_with_all_parameters_valid_succeeds(self):
        """Simulate updating an entity by ID."""
        request_to_validate = {'name': self.resource_name,
                               'description': self.description,
                               'enabled': self.valid_enabled,
                               'url': self.valid_url,
                               'email': self.valid_email}
        self.update_schema_validator.validate(request_to_validate)

    def test_update_entity_with_a_valid_required_parameter_succeeds(self):
        """Succeed if a valid required parameter is provided."""
        request_to_validate = {'name': self.resource_name}
        self.update_schema_validator.validate(request_to_validate)

    def test_update_entity_with_invalid_required_parameter_fails(self):
        """Fail if a provided required parameter is invalid."""
        request_to_validate = {'name': 'a' * 256}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_schema_validator.validate,
                          request_to_validate)

    def test_update_entity_with_missing_required_parameter_succeeds(self):
        """Required parameters are not required for an update."""
        request_to_validate = {'email': self.valid_email}
        self.update_schema_validator.validate(request_to_validate)

    def test_update_entity_with_a_null_optional_parameter_succeeds(self):
        """Optional parameters can be null to removed the value."""
        request_to_validate = {'email': None}
        self.update_schema_validator.validate(request_to_validate)

    def test_update_entity_with_a_valid_optional_parameter_succeeds(self):
        """Succeeds with only a single valid optional parameter."""
        request_to_validate = {'email': self.valid_email}
        self.update_schema_validator.validate(request_to_validate)

    def test_update_entity_with_invalid_optional_parameter_fails(self):
        """Fails when an optional parameter is invalid."""
        request_to_validate = {'email': 0}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_schema_validator.validate,
                          request_to_validate)


class PolicyValidationTestCase(testtools.TestCase):
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
        """Exception raised without `type` in request."""
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


class CredentialValidationTestCase(testtools.TestCase):
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


class RegionValidationTestCase(testtools.TestCase):
    """Test for V3 Region API validation."""

    _valid_url_types = ['https://example.com', 'http://example.com',
                        'http://localhost', 'http://127.0.0.1:5000']
    _invalid_url_types = [False, 'this is not a URL', 1234, 'www.example.com',
                          'localhost']

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

    def test_validate_region_create_succeeds_with_url(self):
        """Validate `url` attribute in region create request."""
        for url in self._valid_url_types:
            request_to_validate = {'url': url}
            self.create_region_validator.validate(request_to_validate)

    def test_validate_region_create_fails_with_invalid_url(self):
        """Exception raised when passing invalid `url` in request."""
        for url in self._invalid_url_types:
            request_to_validate = {'url': url}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_region_validator.validate,
                              request_to_validate)

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

    def test_validate_region_update_succeeds_with_url(self):
        """Validate `url` attribute in region update request."""
        for url in self._valid_url_types:
            request_to_validate = {'url': url}
            self.update_region_validator.validate(request_to_validate)

    def test_validate_region_update_fails_with_invalid_url(self):
        """Exception raised when passing invalid `url` in request."""
        for url in self._invalid_url_types:
            request_to_validate = {'url': url}
            self.assertRaises(exception.SchemaValidationError,
                              self.update_region_validator.validate,
                              request_to_validate)


class ServiceValidationTestCase(testtools.TestCase):
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
        """Validate boolean values as enabled values on service create."""
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

    def test_validate_service_create_fails_when_name_too_long(self):
        """Exception raised when `name` is greater than 255 characters."""
        long_name = 'a' * 256
        request_to_validate = {'type': 'compute',
                               'name': long_name}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_service_validator.validate,
                          request_to_validate)

    def test_validate_service_create_fails_when_name_too_short(self):
        """Exception is raised when `name` is too short."""
        request_to_validate = {'type': 'compute',
                               'name': ''}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_service_validator.validate,
                          request_to_validate)

    def test_validate_service_create_fails_when_type_too_long(self):
        """Exception is raised when `type` is too long."""
        long_type_name = 'a' * 256
        request_to_validate = {'type': long_type_name}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_service_validator.validate,
                          request_to_validate)

    def test_validate_service_create_fails_when_type_too_short(self):
        """Exception is raised when `type` is too short."""
        request_to_validate = {'type': ''}
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
        """Validate updating a service with extra parameters."""
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

    def test_validate_service_update_fails_with_name_too_long(self):
        """Exception is raised when `name` is too long on update."""
        long_name = 'a' * 256
        request_to_validate = {'name': long_name}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_service_validator.validate,
                          request_to_validate)

    def test_validate_service_update_fails_with_name_too_short(self):
        """Exception is raised when `name` is too short on update."""
        request_to_validate = {'name': ''}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_service_validator.validate,
                          request_to_validate)

    def test_validate_service_update_fails_with_type_too_long(self):
        """Exception is raised when `type` is too long on update."""
        long_type_name = 'a' * 256
        request_to_validate = {'type': long_type_name}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_service_validator.validate,
                          request_to_validate)

    def test_validate_service_update_fails_with_type_too_short(self):
        """Exception is raised when `type` is too short on update."""
        request_to_validate = {'type': ''}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_service_validator.validate,
                          request_to_validate)


class EndpointValidationTestCase(testtools.TestCase):
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
            request_to_validate = {'enabled': valid_enabled,
                                   'service_id': uuid.uuid4().hex,
                                   'interface': 'public',
                                   'url': 'https://service.example.com:5000/'}
            self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_create_endpoint_fails_with_invalid_enabled(self):
        """Exception raised when boolean-like values as `enabled`."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': invalid_enabled,
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
