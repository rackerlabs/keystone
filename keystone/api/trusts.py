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

# This file handles all flask-restful resources for /v3/OS-TRUST

# TODO(morgan): Deprecate /v3/OS-TRUST/trusts path in favour of /v3/trusts.
# /v3/OS-TRUST should remain indefinitely.

import functools

import flask
from six.moves import http_client

from keystone import assignment
from keystone.common import json_home
from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone.common import utils
from keystone.common import validation
from keystone import exception
from keystone.i18n import _
from keystone.server import flask as ks_flask
from keystone.trust import schema


ENFORCER = rbac_enforcer.RBACEnforcer
PROVIDERS = provider_api.ProviderAPIs

_build_resource_relation = functools.partial(
    json_home.build_v3_resource_relation, extension_name='OS-TRUST',
    extension_version=1.0)
TRUST_ID_PARAMETER_RELATION = json_home.build_v3_extension_parameter_relation(
    'OS-TRUST', '1.0', 'trust_id')


class TrustResource(ks_flask.ResourceBase):
    collection_key = 'trusts'
    member_key = 'trust'

    def _normalize_trust_data(self, trust):
        # correct isotime and fill in role data
        if trust.get('expires_at') is not None:
            trust['expires_at'] = utils.isotime(trust['expires_at'],
                                                subsecond=True)

        trust_full_roles = []
        for trust_role in trust.get('roles', []):
            trust_role = trust_role['id']
            try:
                matching_role = PROVIDERS.role_api.get_role(trust_role)
                # TODO(morgan): Correct the cross-subsystem call here to allow
                # for local handling of the role wrapping
                full_role = assignment.controllers.RoleV3.wrap_member(
                    self.oslo_context, matching_role['role'])
                trust_full_roles.append(full_role)
            except exception.RoleNotFound:
                pass

        trust['roles'] = trust_full_roles
        trust['role_links'] = {
            'self': ks_flask.base_url() + '/%s/roles' % trust['id'],
            'next': None,
            'previous': None}

    def _check_unrestricted(self):
        token = self.auth_context['token']
        auth_methods = token['methods']
        if 'application_credential' in auth_methods:
            td = token.token_data['token']
            if td['application_credential']['restricted']:
                action = _("Using method 'application_credential' is not "
                           "allowed for managing trusts.")
                raise exception.ForbiddenAction(action=action)

    def _find_redelegated_trust(self):
        # Check if delegated via trust
        redelegated_trust = None
        if self.oslo_context.is_delegated_auth:
            src_trust_id = self.oslo_context.trust_id
            if not src_trust_id:
                action = _('Redelegation allowed for delegated by trust only')
                raise exception.ForbiddenAction(action=action)
            redelegated_trust = PROVIDERS.trust_api.get_trust(src_trust_id)
        return redelegated_trust

    @staticmethod
    def _parse_expiration_date(expiration_date):
        if expiration_date:
            return utils.parse_expiration_date(expiration_date)
        return None

    def _require_trustor_has_role_in_project(self, trust):
        trustor_roles = self._get_trustor_roles(trust)
        for trust_role in trust['roles']:
            matching_roles = [x for x in trustor_roles
                              if x == trust_role['id']]
            if not matching_roles:
                raise exception.RoleNotFound(role_id=trust_role['id'])

    def _get_trustor_roles(self, trust):
        original_trust = trust.copy()
        while original_trust.get('redelegated_trust_id'):
            original_trust = PROVIDERS.trust_api.get_trust(
                original_trust['redelegated_trust_id'])

        if not ((trust.get('project_id')) in [None, '']):
            # Check project exists.
            PROVIDERS.resource_api.get_project(trust['project_id'])
            # Get a list of roles including any domain specific roles
            assignment_list = PROVIDERS.assignment_api.list_role_assignments(
                user_id=original_trust['trustor_user_id'],
                project_id=original_trust['project_id'],
                effective=True, strip_domain=False)
            return list({x['role_id'] for x in assignment_list})
        else:
            return []

    def _normalize_role_list(self, trust_roles):
        roles = []
        for role in trust_roles:
            if role.get('id'):
                roles.append({'id': role['id']})
            else:
                roles.append(
                    PROVIDERS.role_api.get_unique_role_by_name(role['name']))
        return roles

    @ENFORCER.policy_enforcer_action('identity:get_trust')
    def _get_trust(self, trust_id):
        ENFORCER.enforce_call()
        trust = PROVIDERS.trust_api.get_trust(trust_id)
        self._normalize_trust_data(trust)
        return self.wrap_member(trust)

    @ENFORCER.policy_enforcer_action('identity:list_trusts')
    def _list_trusts(self):
        ENFORCER.enforce_call()
        trusts = []
        trustor_user_id = flask.request.args.get('trustor_user_id')
        trustee_user_id = flask.request.args.get('trustee_user_id')

        if not flask.request.args:
            # NOTE(morgan): Admin can list all trusts.
            ENFORCER.enforce_call(action='admin_required')
            trusts += PROVIDERS.trust_api.list_trusts()

        # TODO(morgan): Convert the trustor/trustee checks into policy
        # checkstr we can enforce on. This is duplication of code
        # behavior/design as the OS-TRUST controller for ease of review/
        # comparison of previous code. Minor optimizations [checks before db
        # hits] have been done.
        action = _('Cannot list trusts for another user')
        if trustor_user_id:
            if trustor_user_id != self.oslo_context.user_id:
                raise exception.Forbidden(action=action)

        if trustee_user_id:
            if trustee_user_id != self.oslo_context.user_id:
                raise exception.Forbidden(action=action)

        trusts += PROVIDERS.trust_api.list_trusts_for_trustor(trustor_user_id)
        trusts += PROVIDERS.trust_api.list_trusts_for_trustee(trustee_user_id)

        for trust in trusts:
            # get_trust returns roles, list_trusts does not
            # It seems in some circumstances, roles does not
            # exist in the query response, so check first
            if 'roles' in trust:
                del trust['roles']

            if trust.get('expires_at') is not None:
                trust['expires_at'] = utils.isotime(trust['expires_at'],
                                                    subsecond=True)

        return self.wrap_collection(trusts)

    def get(self, trust_id=None):
        """Dispatch for GET/HEAD or LIST trusts."""
        if trust_id is not None:
            return self._get_trust(trust_id=trust_id)
        else:
            return self._list_trusts()

    @ENFORCER.policy_enforcer_action('identity:create_trust')
    def post(self):
        """Create a new trust.

        The User creating the trust must be the trustor.
        """
        ENFORCER.enforce_call()
        trust = flask.request.json.get('trust', {})
        validation.lazy_validate(schema.trust_create, trust)
        self._check_unrestricted()

        if trust.get('project_id') and not trust.get('roles'):
            action = _('At least one role should be specified')
            raise exception.ForbiddenAction(action=action)

        if self.oslo_context.user_id != trust.get('trustor_user_id'):
            action = _("The authenticated user should match the trustor")
            raise exception.ForbiddenAction(action=action)

        # Ensure the trustee exists
        PROVIDERS.identity_api.get_user(trust['trustee_user_id'])

        # Normalize roles
        trust['roles'] = self._normalize_role_list(trust.get('roles', []))
        self._require_trustor_has_role_in_project(trust)
        trust['expires_at'] = self._parse_expiration_date(
            trust.get('expires_at'))
        self._assign_unique_id(trust)
        redelegated_trust = self._find_redelegated_trust()
        new_trust = PROVIDERS.trust_api.create_trust(
            trust_id=trust['id'],
            trust=trust,
            roles=trust['roles'],
            redelegated_trust=redelegated_trust,
            # TODO(morgan): Fix initiator before merging os-trust -> flask
            initiator=None)
        self._normalize_trust_data(trust)
        return self.wrap_member(new_trust)

    @ENFORCER.policy_enforcer_action('identity:delete_trust')
    def delete(self, trust_id):
        ENFORCER.enforce_call()
        self._check_unrestricted()

        trust = PROVIDERS.trust_api.get_trust(trust_id)

        # TODO(morgan): convert this check to an oslo_policy checkstr that
        # can be referenced/enforced on.
        if (self.oslo_context.user_id != trust.get('trustor_user_id') and
                not self.oslo_context.is_admin):
            action = _('Only admin or trustor can delete a trust')
            raise exception.ForbiddenAction(action=action)

        # TODO(morgan): Fix initiator before merging code.
        PROVIDERS.trust_api.delete_trust(trust_id, initiator=None)


class RolesForTrustListResource(ks_flask.ResourceBase):
    @ENFORCER.policy_enforcer_action('identity:list_roles_for_trust')
    def get(self, trust_id):
        ENFORCER.enforce_call()
        # TODO(morgan): marshal_with "GET_ROLE"


class RolesForTrustResource(ks_flask.ResourceBase):
    @ENFORCER.policy_enforcer_action('identity:get_role_for_trust')
    def get(self, trust_id, role_id):
        """Get a role that has been assigned to a trust."""
        ENFORCER.enforce_call()
        trust = PROVIDERS.trust_api.get_trust('trust_id')
        trustor_trustee_only


class TrustAPI(ks_flask.APIBase):
    _name = 'trusts'
    _import_name = __name__
    resources = [TrustResource]
    resource_mapping = [
        ks_flask.construct_resource_map(
            resource=RolesForTrustListResource,
            url='/trusts/<string:trust_id>/roles',
            resource_kwargs={},
            rel='trust_roles',
            path_vars={
                'trust_id': TRUST_ID_PARAMETER_RELATION},
            resource_relation_func=_build_resource_relation),
        ks_flask.construct_resource_map(
            resource=RolesForTrustResource,
            url='/trusts/<string:trust_id>/roles/<string:role_id>',
            resource_kwargs={},
            rel='trust_roles',
            path_vars={
                'trust_id': TRUST_ID_PARAMETER_RELATION,
                'role_id': json_home.Parameters.ROLE_ID},
            resource_relation_func=_build_resource_relation),
    ]
    collection_key = 'trusts'
    member_key = 'trust'
    _api_url_prefix = '/OS-TRUSTS'


APIs = (TrustAPI,)
