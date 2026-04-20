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

# This file handles flask-restful resources for
# /v3/OS-IP-ALLOWLIST/{users,domains,projects}/{id}/cidrs

import functools
import http.client
from typing import Any, Callable, Optional

import flask
import flask_restful

from keystone.common import json_home
from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone import exception as ks_exception
from keystone.server import flask as ks_flask

PROVIDERS = provider_api.ProviderAPIs
ENFORCER = rbac_enforcer.RBACEnforcer


def _build_user_target_enforcement():
    target = {}
    try:
        target['user'] = PROVIDERS.identity_api.get_user(
            flask.request.view_args.get('user_id')
        )
    except ks_exception.NotFound:  # nosec
        # Defer notfound downstream
        pass
    return target


def _build_domain_target_enforcement():
    target = {}
    try:
        target['domain'] = PROVIDERS.resource_api.get_domain(
            flask.request.view_args.get('domain_id')
        )
    except ks_exception.NotFound:  # nosec
        pass
    return target


def _build_project_target_enforcement():
    target = {}
    try:
        target['project'] = PROVIDERS.resource_api.get_project(
            flask.request.view_args.get('project_id')
        )
    except ks_exception.NotFound:  # nosec
        pass
    return target


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


def _self_url(target_type, target_id):
    return ks_flask.base_url(
        path='/OS-IP-ALLOWLIST/%ss/%s/cidrs' % (target_type, target_id)
    )


class _BaseCIDRsResource(flask_restful.Resource):
    """Shared GET (list) / POST (create) behavior for all target types."""

    target_type: str = ''  # 'user' | 'domain' | 'project'
    list_action: str = ''
    create_action: str = ''
    build_target_fn: Optional[Callable[[], dict[str, Any]]] = None

    def _list(self, target_id):
        ENFORCER.enforce_call(action=self.list_action)
        entries = PROVIDERS.ip_allowlist_api.list_allowed_cidrs(
            self.target_type, target_id
        )
        return {
            'cidrs': entries,
            'links': {
                'self': _self_url(self.target_type, target_id),
                'next': None,
                'previous': None,
            },
        }

    def _create(self, target_id):
        ENFORCER.enforce_call(
            action=self.create_action,
            build_target=self.__class__.build_target_fn,
        )
        body = flask.request.get_json(force=True)
        entry = body.get('cidr', {})
        ref = PROVIDERS.ip_allowlist_api.create_allowed_cidr(
            self.target_type, target_id, entry
        )
        return {'cidr': ref}, http.client.CREATED


class _BaseCIDRResource(flask_restful.Resource):
    """Shared GET / DELETE behavior for a single entry."""

    target_type: str = ''
    get_action: str = ''
    delete_action: str = ''
    build_target_fn: Optional[Callable[[], dict[str, Any]]] = None

    def _get(self, target_id, entry_id):
        ENFORCER.enforce_call(action=self.get_action)
        ref = PROVIDERS.ip_allowlist_api.get_allowed_cidr(
            self.target_type, target_id, entry_id
        )
        return {'cidr': ref}

    def _delete(self, target_id, entry_id):
        ENFORCER.enforce_call(
            action=self.delete_action,
            build_target=self.__class__.build_target_fn,
        )
        PROVIDERS.ip_allowlist_api.delete_allowed_cidr(
            self.target_type, target_id, entry_id
        )
        return None, http.client.NO_CONTENT


# -- user --------------------------------------------------------------------

class UserIPAllowlistCIDRsResource(_BaseCIDRsResource):
    target_type = 'user'
    list_action = 'identity:list_user_ip_allowlist_cidrs'
    create_action = 'identity:create_user_ip_allowlist_cidr'
    build_target_fn = staticmethod(_build_user_target_enforcement)

    def get(self, user_id):
        return self._list(user_id)

    def post(self, user_id):
        return self._create(user_id)


class UserIPAllowlistCIDRResource(_BaseCIDRResource):
    target_type = 'user'
    get_action = 'identity:get_user_ip_allowlist_cidr'
    delete_action = 'identity:delete_user_ip_allowlist_cidr'
    build_target_fn = staticmethod(_build_user_target_enforcement)

    def get(self, user_id, entry_id):
        return self._get(user_id, entry_id)

    def delete(self, user_id, entry_id):
        return self._delete(user_id, entry_id)


# -- domain ------------------------------------------------------------------

class DomainIPAllowlistCIDRsResource(_BaseCIDRsResource):
    target_type = 'domain'
    list_action = 'identity:list_domain_ip_allowlist_cidrs'
    create_action = 'identity:create_domain_ip_allowlist_cidr'
    build_target_fn = staticmethod(_build_domain_target_enforcement)

    def get(self, domain_id):
        return self._list(domain_id)

    def post(self, domain_id):
        return self._create(domain_id)


class DomainIPAllowlistCIDRResource(_BaseCIDRResource):
    target_type = 'domain'
    get_action = 'identity:get_domain_ip_allowlist_cidr'
    delete_action = 'identity:delete_domain_ip_allowlist_cidr'
    build_target_fn = staticmethod(_build_domain_target_enforcement)

    def get(self, domain_id, entry_id):
        return self._get(domain_id, entry_id)

    def delete(self, domain_id, entry_id):
        return self._delete(domain_id, entry_id)


# -- project -----------------------------------------------------------------

class ProjectIPAllowlistCIDRsResource(_BaseCIDRsResource):
    target_type = 'project'
    list_action = 'identity:list_project_ip_allowlist_cidrs'
    create_action = 'identity:create_project_ip_allowlist_cidr'
    build_target_fn = staticmethod(_build_project_target_enforcement)

    def get(self, project_id):
        return self._list(project_id)

    def post(self, project_id):
        return self._create(project_id)


class ProjectIPAllowlistCIDRResource(_BaseCIDRResource):
    target_type = 'project'
    get_action = 'identity:get_project_ip_allowlist_cidr'
    delete_action = 'identity:delete_project_ip_allowlist_cidr'
    build_target_fn = staticmethod(_build_project_target_enforcement)

    def get(self, project_id, entry_id):
        return self._get(project_id, entry_id)

    def delete(self, project_id, entry_id):
        return self._delete(project_id, entry_id)


class OSIPAllowlistAPI(ks_flask.APIBase):
    _name = 'OS-IP-ALLOWLIST'
    _import_name = __name__
    _api_url_prefix = '/OS-IP-ALLOWLIST'
    resources = []
    resource_mapping = [
        # user
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
        # domain
        ks_flask.construct_resource_map(
            resource=DomainIPAllowlistCIDRsResource,
            url='/domains/<string:domain_id>/cidrs',
            resource_kwargs={},
            rel='domain_ip_allowlist_cidrs',
            resource_relation_func=_build_resource_relation,
            path_vars={
                'domain_id': _build_parameter_relation(
                    parameter_name='domain_id'
                ),
            },
        ),
        ks_flask.construct_resource_map(
            resource=DomainIPAllowlistCIDRResource,
            url='/domains/<string:domain_id>/cidrs/<string:entry_id>',
            resource_kwargs={},
            rel='domain_ip_allowlist_cidr',
            resource_relation_func=_build_resource_relation,
            path_vars={
                'domain_id': _build_parameter_relation(
                    parameter_name='domain_id'
                ),
                'entry_id': _build_parameter_relation(
                    parameter_name='entry_id'
                ),
            },
        ),
        # project
        ks_flask.construct_resource_map(
            resource=ProjectIPAllowlistCIDRsResource,
            url='/projects/<string:project_id>/cidrs',
            resource_kwargs={},
            rel='project_ip_allowlist_cidrs',
            resource_relation_func=_build_resource_relation,
            path_vars={
                'project_id': _build_parameter_relation(
                    parameter_name='project_id'
                ),
            },
        ),
        ks_flask.construct_resource_map(
            resource=ProjectIPAllowlistCIDRResource,
            url='/projects/<string:project_id>/cidrs/<string:entry_id>',
            resource_kwargs={},
            rel='project_ip_allowlist_cidr',
            resource_relation_func=_build_resource_relation,
            path_vars={
                'project_id': _build_parameter_relation(
                    parameter_name='project_id'
                ),
                'entry_id': _build_parameter_relation(
                    parameter_name='entry_id'
                ),
            },
        ),
    ]


APIs = (OSIPAllowlistAPI,)
