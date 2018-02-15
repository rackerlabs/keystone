# Copyright 2013 OpenStack Foundation
#
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

from oslo_log import log

from keystone.auth import core
from keystone.auth import schema
from keystone.common import authorization
from keystone.common import controller
from keystone.common import provider_api
from keystone.common import wsgi
import keystone.conf
from keystone import exception
from keystone.i18n import _
from keystone.resource import controllers as resource_controllers


LOG = log.getLogger(__name__)

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class Auth(controller.V3Controller):

    # Note(atiwari): From V3 auth controller code we are
    # calling protection() wrappers, so we need to setup
    # the member_name and  collection_name attributes of
    # auth controller code.
    # In the absence of these attributes, default 'entity'
    # string will be used to represent the target which is
    # generic. Policy can be defined using 'entity' but it
    # would not reflect the exact entity that is in context.
    # We are defining collection_name = 'tokens' and
    # member_name = 'token' to facilitate policy decisions.
    collection_name = 'tokens'
    member_name = 'token'

    def __init__(self, *args, **kw):
        super(Auth, self).__init__(*args, **kw)
        keystone.conf.auth.setup_authentication()

    def authenticate_for_token(self, request, auth=None):
        """Authenticate user and issue a token."""
        schema.validate_issue_token_auth(auth)
        token_id, token_data = core.AuthHelper.auth_for_token_webob(
            request, auth)
        return render_token_data_response(token_id, token_data, created=True)

    @controller.protected()
    def check_token(self, request):
        token_id = request.subject_token
        window_seconds = authorization.token_validation_window(request)
        token_data = PROVIDERS.token_provider_api.validate_token(
            token_id, window_seconds=window_seconds)
        # NOTE(morganfainberg): The code in
        # ``keystone.common.wsgi.render_response`` will remove the content
        # body.
        return render_token_data_response(token_id, token_data)

    @controller.protected()
    def revoke_token(self, request):
        return PROVIDERS.token_provider_api.revoke_token(request.subject_token)

    @controller.protected()
    def validate_token(self, request):
        token_id = request.subject_token
        window_seconds = authorization.token_validation_window(request)
        include_catalog = 'nocatalog' not in request.params
        token_data = PROVIDERS.token_provider_api.validate_token(
            token_id, window_seconds=window_seconds)
        if not include_catalog and 'catalog' in token_data['token']:
            del token_data['token']['catalog']
        return render_token_data_response(token_id, token_data)

    def revocation_list(self, request):
        if not CONF.token.revoke_by_id:
            raise exception.Gone()
        # NOTE(lbragstad): This API is deprecated and isn't supported. Keystone
        # also doesn't store tokens, so returning a list of revoked tokens
        # would require keystone to write invalid tokens to disk, which defeats
        # the purpose. Return a 403 instead of removing the API all together.
        # The alternative would be to return a signed response of just an empty
        # list.
        raise exception.Forbidden()

    def _combine_lists_uniquely(self, a, b):
        # it's most likely that only one of these will be filled so avoid
        # the combination if possible.
        if a and b:
            return {x['id']: x for x in a + b}.values()
        else:
            return a or b

    @controller.protected()
    def get_auth_projects(self, request):
        user_id = request.auth_context.get('user_id')
        group_ids = request.auth_context.get('group_ids')

        user_refs = []
        if user_id:
            try:
                user_refs = PROVIDERS.assignment_api.list_projects_for_user(
                    user_id
                )
            except exception.UserNotFound:  # nosec
                # federated users have an id but they don't link to anything
                pass

        grp_refs = []
        if group_ids:
            grp_refs = PROVIDERS.assignment_api.list_projects_for_groups(
                group_ids
            )

        refs = self._combine_lists_uniquely(user_refs, grp_refs)
        return resource_controllers.ProjectV3.wrap_collection(
            request.context_dict, refs)

    @controller.protected()
    def get_auth_domains(self, request):
        user_id = request.auth_context.get('user_id')
        group_ids = request.auth_context.get('group_ids')

        user_refs = []
        if user_id:
            try:
                user_refs = PROVIDERS.assignment_api.list_domains_for_user(
                    user_id
                )
            except exception.UserNotFound:  # nosec
                # federated users have an id but they don't link to anything
                pass

        grp_refs = []
        if group_ids:
            grp_refs = PROVIDERS.assignment_api.list_domains_for_groups(
                group_ids
            )

        refs = self._combine_lists_uniquely(user_refs, grp_refs)
        return resource_controllers.DomainV3.wrap_collection(
            request.context_dict, refs)

    @controller.protected()
    def get_auth_system(self, request):
        user_id = request.auth_context.get('user_id')
        group_ids = request.auth_context.get('group_ids')

        user_assignments = []
        if user_id:
            try:
                user_assignments = (
                    PROVIDERS.assignment_api.list_system_grants_for_user(
                        user_id
                    )
                )
            except exception.UserNotFound:  # nosec
                # federated users have an id but they don't link to anything
                pass

        group_assignments = []
        if group_ids:
            group_assignments = (
                PROVIDERS.assignment_api.list_system_grants_for_group(
                    group_ids
                )
            )

        assignments = self._combine_lists_uniquely(
            user_assignments, group_assignments
        )
        if assignments:
            response = {
                'system': [{'all': True}],
                'links': {
                    'self': self.base_url(
                        request.context_dict, path='auth/system'
                    )
                }
            }
        else:
            response = {
                'system': [],
                'links': {
                    'self': self.base_url(
                        request.context_dict, path='auth/system'
                    )
                }
            }
        return response

    @controller.protected()
    def get_auth_catalog(self, request):
        user_id = request.auth_context.get('user_id')
        project_id = request.auth_context.get('project_id')

        if not project_id:
            raise exception.Forbidden(
                _('A project-scoped token is required to produce a service '
                  'catalog.'))

        # The V3Controller base methods mostly assume that you're returning
        # either a collection or a single element from a collection, neither of
        # which apply to the catalog. Because this is a special case, this
        # re-implements a tiny bit of work done by the base controller (such as
        # self-referential link building) to avoid overriding or refactoring
        # several private methods.
        return {
            'catalog': PROVIDERS.catalog_api.get_v3_catalog(
                user_id, project_id
            ),
            'links': {'self': self.base_url(request.context_dict,
                                            path='auth/catalog')}
        }


# FIXME(gyee): not sure if it belongs here or keystone.common. Park it here
# for now.
def render_token_data_response(token_id, token_data, created=False):
    """Render token data HTTP response.

    Stash token ID into the X-Subject-Token header.

    """
    headers = [('X-Subject-Token', token_id)]

    if created:
        status = (201, 'Created')
    else:
        status = (200, 'OK')

    return wsgi.render_response(body=token_data,
                                status=status, headers=headers)
