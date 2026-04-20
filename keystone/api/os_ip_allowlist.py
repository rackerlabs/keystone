# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This file handles all flask-restful resources for
# /v3/OS-IP-ALLOWLIST/users/{user_id}/cidrs

import functools
import http.client

import flask
import flask_restful

from keystone.api._shared import json_home_relations
from keystone.common import json_home
from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone.server import flask as ks_flask

PROVIDERS = provider_api.ProviderAPIs
ENFORCER = rbac_enforcer.RBACEnforcer

_build_resource_relation = functools.partial(
    json_home.build_v3_extension_resource_relation,
    extension_name='OS-IP-ALLOWLIST',
    extension_version='1.0',
)
_build_parameter_relation = functools.partial(
    json_home.build_v3_extension_parameter_relation,
    extension_name='OS-IP-ALLOWLIST',
    extension_version='1.0',
)


class UserIPAllowlistCIDRsResource(flask_restful.Resource):
    """GET and POST on /users/{user_id}/cidrs."""

    def get(self, user_id):
        ENFORCER.enforce_call(action='identity:list_ip_allowlist_cidrs')
        entries = PROVIDERS.ip_allowlist_api.list_allowed_cidrs(user_id)
        return {
            'cidrs': entries,
            'links': {
                'self': ks_flask.base_url(
                    path='/OS-IP-ALLOWLIST/users/%s/cidrs' % user_id
                ),
                'next': None,
                'previous': None,
            },
        }

    def post(self, user_id):
        ENFORCER.enforce_call(action='identity:create_ip_allowlist_cidr')
        body = flask.request.get_json(force=True)
        entry = body.get('cidr', {})
        ref = PROVIDERS.ip_allowlist_api.create_allowed_cidr(user_id, entry)
        return {'cidr': ref}, http.client.CREATED


class UserIPAllowlistCIDRResource(flask_restful.Resource):
    """GET and DELETE on /users/{user_id}/cidrs/{entry_id}."""

    def get(self, user_id, entry_id):
        ENFORCER.enforce_call(action='identity:get_ip_allowlist_cidr')
        ref = PROVIDERS.ip_allowlist_api.get_allowed_cidr(user_id, entry_id)
        return {'cidr': ref}

    def delete(self, user_id, entry_id):
        ENFORCER.enforce_call(action='identity:delete_ip_allowlist_cidr')
        PROVIDERS.ip_allowlist_api.delete_allowed_cidr(user_id, entry_id)
        return None, http.client.NO_CONTENT


class OSIPAllowlistAPI(ks_flask.APIBase):
    _name = 'OS-IP-ALLOWLIST'
    _import_name = __name__
    _api_url_prefix = '/OS-IP-ALLOWLIST'
    resources = []
    resource_mapping = [
        ks_flask.construct_resource_map(
            resource=UserIPAllowlistCIDRsResource,
            url='/users/<string:user_id>/cidrs',
            resource_kwargs={},
            rel='user_ip_allowlist_cidrs',
            resource_relation_func=_build_resource_relation,
            path_vars={
                'user_id': _build_parameter_relation(
                    parameter_name='user_id'
                ),
            },
        ),
        ks_flask.construct_resource_map(
            resource=UserIPAllowlistCIDRResource,
            url='/users/<string:user_id>/cidrs/<string:entry_id>',
            resource_kwargs={},
            rel='user_ip_allowlist_cidr',
            resource_relation_func=_build_resource_relation,
            path_vars={
                'user_id': _build_parameter_relation(
                    parameter_name='user_id'
                ),
                'entry_id': _build_parameter_relation(
                    parameter_name='entry_id'
                ),
            },
        ),
    ]


APIs = (OSIPAllowlistAPI,)
