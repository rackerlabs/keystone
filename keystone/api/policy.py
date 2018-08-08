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

# This file handles all flask-restful resources for /policy

import flask
from oslo_log import versionutils
import six
from six.moves import http_client

from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone.common import validation
from keystone.policy import schema
from keystone.server import flask as ks_flask

ENFORCER = rbac_enforcer.RBACEnforcer
PROVIDERS = provider_api.ProviderAPIs


def policy_deprecated(f):
    @six.wraps(f)
    def wrapper(*args, **kwargs):
        deprecated = versionutils.deprecated(
            what=f.__name__.upper() + ' of the v3 Policy APIs',
            as_of=versionutils.deprecated.QUEENS)
        return deprecated(f)
    return wrapper()


class PolicyResource(ks_flask.ResourceBase):
    collection_key = 'policies'
    member_key = 'policy'

    @policy_deprecated
    def get(self, policy_id=None):
        if policy_id:
            return self._get_policy(policy_id)
        return self._list_policies()

    def _get_policy(self, policy_id):
        ENFORCER.enforce_call(action='identity:get_policy')
        ref = PROVIDERS.policy_api.get_policy(policy_id)
        return self.wrap_member(ref), http_client.OK

    def _list_policies(self):
        ENFORCER.enforce_call(action='identity:list_policies')

        filters = ['type']
        hints = self.build_driver_hints(filters)
        refs = PROVIDERS.policy_api.list_policies(hints=hints)
        return self.wrap_collection(refs, hints=hints), http_client.OK

    @policy_deprecated
    def post(self):
        ENFORCER.enforce_call(action='identity:create_policy')

        request_body = flask.request.get_json(silent=True, force=True) or {}
        policy_body = request_body.get('policy', {})
        validation.lazy_validate(schema.policy_create, policy_body)
        policy = self._assign_unique_id(self._normalize_dict(policy_body))

        ref = PROVIDERS.policy_api.create_policy(
            policy['id'], policy, initiator=self.audit_initiator
        )
        return self.wrap_member(ref), http_client.CREATED

    @policy_deprecated
    def patch(self, policy_id):
        ENFORCER.enforce_call(action='identity:update_policy')

        request_body = flask.request.get_json(silent=True, force=True) or {}
        policy_body = request_body.get('policy', {})
        validation.lazy_validate(schema.policy_update, policy_body)

        ref = PROVIDERS.policy_api.update_policy(
            policy_id, policy_body, initiator=self.audit_initiator
        )
        return self.wrap_member(ref), http_client.OK

    @policy_deprecated
    def delete(self, policy_id):
        ENFORCER.enforce_call(action='identity:delete_policy')
        res = PROVIDERS.policy_api.delete_policy(
            policy_id, initiator=self.audit_initiator
        )
        return (res, http_client.NO_CONTENT)


class PolicyAPI(ks_flask.APIBase):
    _name = 'policy'
    _import_name = __name__
    _api_url_prefix = '/policy'
    resources = [PolicyResource]
    resource_mapping = []

APIs = (PolicyAPI,)
