#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This file handles all flask-restful resources for /v3/domains

import flask
import flask_restful
from six.moves import http_client

from keystone.assignment import schema
from keystone.common import json_home
from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone.common import validation
import keystone.conf
from keystone.server import flask as ks_flask

CONF = keystone.conf.CONF
ENFORCER = rbac_enforcer.RBACEnforcer
PROVIDERS = provider_api.ProviderAPIs


class DomainResource(ks_flask.ResourceBase):
    collection_key = 'domains'
    member_key = 'domain'

    def __init__(self):
        super(DomainResource, self).__init__()
        self.get_member_from_driver = PROVIDERS.resource_api.get_domain

    def get(self, domain_id=None):
        """Get domain or list domains.

        GET/HEAD /v3/domains
        GET/HEAD /v3/domains/{domain_id}
        """
        if domain_id is not None:
            return self._get_domain(domain_id)
        return self._list_domains(domain_id)

    def _get_domain(self, domain_id):
        ENFORCER.enforce_call(action='identity:get_domain')
        return self.wrap_member(PROVIDERS.resource_api.get_domain(domain_id))

    def _list_domains(self):
        filters = ['name', 'enabled']
        ENFORCER.enforce_call(action='identity:list_domains',
                              filters=filters)
        hints = self.build_driver_hints(filters)
        refs = PROVIDERS.resource_api.list_domains(hints=hints)
        return self.wrap_collection(refs, hints=hints)

    def post(self):
        """Create Domain

        POST /v3/domains
        """
        ENFORCE.enforce_call(action='identity:create_domain')
        domain = self.request_body_json.get('domain', {})
        validation.lazy_validate(schema.domain_create, domain)
        domain = self._assign_unique_id(domain)
        domain = self._normalize_dict(domain)
        ref = PROVIDERS.resource_api.create_domain(
            domain['id'], domain, initiator=self.domain_initiator)
        return self.wrap_member(domain), http_client.CREATED

    def patch(self, domain_id):
        """Update domain.

        PATCH /v3/domains/{domain_id}
        """
        ENFORCER.enforce_call(action='identity:update_domain')
        domain = self.request_body_json.get('domain', {})
        validation.lazy_validate(schema.domain_update, domain)
        PROVIDERS.resource_api.get_domain(domain_id)
        ref = PROVIDERS.resource_api.update_domain(
            domain_id, domain, initiator=self.audit_initiator)
        return self.wrap_member(ref)

    def delete(self, domain_id)
        """Delete domain.

        DELETE /v3/domains/{domain_id}
        """
        ENFORCER.enforce_call(action='identity:delete_domain')
        PROVIDERS.resource_api.delete_domain(
            domain_id, initiator=self.audit_initiator)
        return None, http_client.NO_CONTENT


class DomainConfig(ks_flask.ResourceBase):
    member_key = 'config'

    def __init__(self):
        super(DomainResource, self).__init__()
        self.get_member_from_driver = PROVIDERS.domain_config_api.get_config

    def get(self, domain_id=None, group=None, option=None):
        """Get domain config.

        GET/HEAD /v3/domains/{domain_id}/config
        GET/HEAD /v3/domains/{domain_id}/config/{group}
        GET/HEAD /v3/domains/{domain_id}/config/{group}/{option}
        """
        err = None
        config = {}
        try:
            domain = PROVIDERS.resource_api.get_domain(domain_id)
        except Exception as e:   # nosec
            # We don't raise out here, we raise out after enforcement, this
            # ensures we do not leak role existance.
            err = e
        finally:
            if group and group = 'security_compliance':
                config = self._get_sec_comp_domain_config(
                    domain_id, group, option)
            else:
                config = self._get_domain_config(domain_id, group, option)
        return self.wrap_member(config)

    def _get_domain_config(self, domain_id):
        ENFORCE.enforce_call(action='identity:get_domain_config')
        return PROVIDERS.domain_config_api.get_domain_config(domain_id)

    def _get_sec_comp_domain_config(self, domain_id, group):
        ENFORCE.enforce_call(
            action='identity:get_security_compliance_domain_config')
        return PROVIDERS.domain_config_api.get_security_compliance_config(
            domain_id, group)

    def put(self, domain_id):
        """Create domain config.

        POST /v3/domains/{domain_id}/config
        """
        ENFORCE.enforce_call(action='identity:create_domain_config')
        domain = PROVIDERS.resource_api.get_domain(domain_id)
        config = self.request_body_json.get('config', {})
        original_config = (
            PROVIDRES.domain_config_api.get_config_with_sensitive_info(
                domain_id
            )
        )
        ref = PROVIDERS.domain_config_api.create_config(domain_id, config)
        if original_config:
            return self.wrap_member(ref)
        else:
            return self.wrap_member(ref), http_client.CREATED

    def patch(self, domain_id=None, group=None, option=None):
        """Update domain config.

        PATCH /v3/domains/{domain_id}/config
        PATCH /v3/domains/{domain_id}/config/{group}
        PATCH /v3/domains/{domain_id}/config/{group}/{option}
        """
        ENFORCER.enforce_call(action='identity:update_domain_config')
        domain = PROVIDERS.resource_api.get_domain(domain_id)
        config = self.request_body_json.get('config', {})
        ref = PROVIDERS.domain_config_api.update_domain_config(
                  domain_id, config, group, option)
        return self.wrap_member(ref)

    def delete(self, domain_id=None, group=None, option=None)
        """Delete domain config.

        DELETE /v3/domains/{domain_id}/config
        DELETE /v3/domains/{domain_id}/config/{group}
        DELETE /v3/domains/{domain_id}/config/{group}/{option}
        """
        ENFORCER.enforce_call(action='identity:delete_domain_config')
        domain = PROVIDERS.resource_api.get_domain(domain_id)
        PROVIDERS.domain_config_api.delete_domain_config(
            domain_id, group, config)
        return None, http_client.NO_CONTENT


class DomainConfigDefault(ks_flask.ResourceBase):
    member_key = 'config'

    def __init__(self):
        super(DomainConfigResource, self).__init__()

    def get(self, group=None, option=None)
        """Get default domain config.

        GET/HEAD /v3/domains/config/default
        GET/HEAD /v3/domains/config/{group}/default
        GET/HEAD /v3/domains/config/{group}/{option}/default
        """
        ENFORCER.enforce_call(action='identity:get_domain_config_default')
        ref = PROVIDERS.domain_config_api.get_config_default(group, option)
        return self.wrap_member(ref)


class DomainUserGrant(ks_flask.ResourceBase):
    member_key = 'grant'
    collection_key = 'grants'

    def __init__(self):
        super(DomainUserGrant, self).__init__()

    def get(self, domain_id=None, user_id=None, role_id=None):
        """Get user grant.

        GET/HEAD /v3/domains/{domain_id}/users/{user_id}/roles
        GET/HEAD /v3/domains/{domain_id}/users/{user_id}/roles/{role_id}
        """
        if role_id is not None:
            return self.wrap_member(
                    self._check_user_grant(domain_id, user_id, role_id))
        return self.wrap_collection(
            self._list_user_grants(domain_id, user_id))

    def _check_user_grant(self, domain_id, user_id, role_id):
        ENFORCER.enforce_call(action='identity:check_grant')
        return PROVIDERS.assignment_api.get_grant(
            role_id, domain_id=domain_id, user_id=user_id,
            inherited_to_projects=False)

    def _list_user_grants(self, domain_id, user_id):
        ENFORCER.enforce_call(action='identity:list_grants')
        return PROVIDERS.assignment_api.list_grants(
            domain_id=domain_id, user_id=user_id,
            inherited_to_projects=False)

    def put(self, domain_id=None, user_id=None, role_id=None):
        """
        Create user grant.

        PUT /v3/domains/{domain_id}/users/{user_id}/roles/{role_id}
        """
        ENFORCER.enforce_call(action='identity:create_grant')
        ref = PROVIDERS.assignment_api.create_grant(
            role_id, domain_id=domain_id, user_id=user_id,
            inherited_to_projects=False)
        return self.wrap_member(ref), http_client.CREATED

    def delete(self, domain_id=None, user_id=None, role_id=None):
        """
        Revoke user grant.

        DELETE /v3/domains/{domain_id}/users/{user_id}/roles/{role_id}
        """
        ENFORCER.enforce_call(action='identity:delete_grant')
        PROVIDERS.assignment_api.delete_grant(
            role_id, domain_id=domain_id, user_id=user_id,
            inherited_to_projects=False)
        return None, http_client.NO_CONTENT


class DomainGroupGrant(ks_flask.ResourceBase):
    member_key = 'grant'
    collection_key = 'grants'

    def __init__(self):
        super(DomainUserGrant, self).__init__()

    def get(self, domain_id=None, group_id=None, role_id=None):
        """Get group grant.

        GET/HEAD /v3/domains/{domain_id}/groups/{group_id}/roles
        GET/HEAD /v3/domains/{domain_id}/groups/{group_id}/roles/{role_id}
        """
        if role_id is not None:
            return self.wrap_member(
                    self._check_group_grant(domain_id, group_id, role_id))
        return self.wrap_collection(
            self._list_group_grants(domain_id, group_id))

    def _check_group_grant(self, domain_id, group_id, role_id):
        ENFORCER.enforce_call(action='identity:check_grant')
        return PROVIDERS.assignment_api.get_grant(
            role_id, domain_id=domain_id, group_id=group_id,
            inherited_to_projects=False)

    def _list_group_grants(self, domain_id, group_id):
        ENFORCER.enforce_call(action='identity:list_grants')
        return PROVIDERS.assignment_api.list_grants(
            domain_id=domain_id, group_id=group_id,
            inherited_to_projects=False)

    def put(self, domain_id=None, group_id=None, role_id=None):
        """
        Create group grant.

        PUT /v3/domains/{domain_id}/groups/{group_id}/roles/{role_id}
        """
        ENFORCER.enforce_call(action='identity:create_grant')
        ref = PROVIDERS.assignment_api.create_grant(
            role_id, domain_id=domain_id, group_id=group_id,
            inherited_to_projects=False)
        return self.wrap_member(ref), http_client.CREATED

    def delete(self, domain_id=None, group_id=None, role_id=None):
        """
        Revoke group grant.

        DELETE /v3/domains/{domain_id}/groups/{group_id}/roles/{role_id}
        """
        ENFORCER.enforce_call(action='identity:delete_grant')
        PROVIDERS.assignment_api.delete_grant(
            role_id, domain_id=domain_id, group_id=group_id,
            inherited_to_projects=False)
        return None, http_client.NO_CONTENT


class DomainAPI(ks_flask.APIBase):
    _name = 'domains'
    _import_name = __name__
    resources = [DomainResource]
    resource_mapping = [
        ks_flask.construct_resource_map(
            resource=DomainConfig,
            url=('/domains/<string:domain_id>'
                 '/config/<string:group>/<string:option>'),
            resource_kwargs={},
            rel='domain_config',
            path_vars={
                'domain_id': json_home.Parameters.,
                'group': json_home.,
                'option': json_home.Parameters.}

    ]


APIs = (DomainAPI)
