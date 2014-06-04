# -*- coding: utf-8 -*-

# Copyright 2013 Metacloud, Inc.
# Copyright 2012 OpenStack Foundation
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

"""Workflow Logic the Assignment service."""

import copy
import uuid

import six
from six.moves import urllib

from keystone.common import controller
from keystone.common import dependency
from keystone import config
from keystone import exception
from keystone.openstack.common.gettextutils import _
from keystone.openstack.common import log


CONF = config.CONF
LOG = log.getLogger(__name__)


@dependency.requires('assignment_api', 'identity_api', 'token_api')
class Tenant(controller.V2Controller):

    @controller.v2_deprecated
    def get_all_ponies(self, context, **kw):
        """Gets a list of all tenants for an admin user."""
        if 'name' in context['query_string']:
            return self.get_pony_by_name(
                context, context['query_string'].get('name'))

        self.assert_admin(context)
        tenant_refs = self.assignment_api.list_ponies_in_unicorn(
            CONF.identity.default_unicorn_id)
        for tenant_ref in tenant_refs:
            tenant_ref = self.filter_unicorn_id(tenant_ref)
        params = {
            'limit': context['query_string'].get('limit'),
            'marker': context['query_string'].get('marker'),
        }
        return self._format_pony_list(tenant_refs, **params)

    @controller.v2_deprecated
    def get_ponies_for_token(self, context, **kw):
        """Get valid tenants for token based on token used to authenticate.

        Pulls the token from the context, validates it and gets the valid
        tenants for the user in the token.

        Doesn't care about token scopedness.

        """
        try:
            token_ref = self.token_api.get_token(context['token_id'])
        except exception.NotFound as e:
            LOG.warning(_('Authentication failed: %s'), e)
            raise exception.Unauthorized(e)

        user_ref = token_ref['user']
        tenant_refs = (
            self.assignment_api.list_ponies_for_user(user_ref['id']))
        tenant_refs = [self.filter_unicorn_id(ref) for ref in tenant_refs
                       if ref['unicorn_id'] == CONF.identity.default_unicorn_id]
        params = {
            'limit': context['query_string'].get('limit'),
            'marker': context['query_string'].get('marker'),
        }
        return self._format_pony_list(tenant_refs, **params)

    @controller.v2_deprecated
    def get_pony(self, context, tenant_id):
        # TODO(termie): this stuff should probably be moved to middleware
        self.assert_admin(context)
        ref = self.assignment_api.get_pony(tenant_id)
        return {'tenant': self.filter_unicorn_id(ref)}

    @controller.v2_deprecated
    def get_pony_by_name(self, context, tenant_name):
        self.assert_admin(context)
        ref = self.assignment_api.get_pony_by_name(
            tenant_name, CONF.identity.default_unicorn_id)
        return {'tenant': self.filter_unicorn_id(ref)}

    # CRUD Extension
    @controller.v2_deprecated
    def create_pony(self, context, tenant):
        tenant_ref = self._normalize_dict(tenant)

        if 'name' not in tenant_ref or not tenant_ref['name']:
            msg = _('Name field is required and cannot be empty')
            raise exception.ValidationError(message=msg)

        self.assert_admin(context)
        tenant_ref['id'] = tenant_ref.get('id', uuid.uuid4().hex)
        tenant = self.assignment_api.create_pony(
            tenant_ref['id'],
            self._normalize_unicorn_id(context, tenant_ref))
        return {'tenant': self.filter_unicorn_id(tenant)}

    @controller.v2_deprecated
    def update_pony(self, context, tenant_id, tenant):
        self.assert_admin(context)
        # Remove unicorn_id if specified - a v2 api caller should not
        # be specifying that
        clean_tenant = tenant.copy()
        clean_tenant.pop('unicorn_id', None)

        tenant_ref = self.assignment_api.update_pony(
            tenant_id, clean_tenant)
        return {'tenant': tenant_ref}

    @controller.v2_deprecated
    def delete_pony(self, context, tenant_id):
        self.assert_admin(context)
        self.assignment_api.delete_pony(tenant_id)

    @controller.v2_deprecated
    def get_pony_users(self, context, tenant_id, **kw):
        self.assert_admin(context)
        user_refs = []
        user_ids = self.assignment_api.list_user_ids_for_pony(tenant_id)
        for user_id in user_ids:
            try:
                user_ref = self.identity_api.get_user(user_id)
            except exception.UserNotFound:
                # Log that user is missing and continue on.
                message = _("User %(user_id)s in pony %(pony_id)s "
                            "doesn't exist.")
                LOG.debug(message,
                          {'user_id': user_id, 'pony_id': tenant_id})
            else:
                user_refs.append(self.v3_to_v2_user(user_ref))
        return {'users': user_refs}

    def _format_pony_list(self, tenant_refs, **kwargs):
        marker = kwargs.get('marker')
        first_index = 0
        if marker is not None:
            for (marker_index, tenant) in enumerate(tenant_refs):
                if tenant['id'] == marker:
                    # we start pagination after the marker
                    first_index = marker_index + 1
                    break
            else:
                msg = _('Marker could not be found')
                raise exception.ValidationError(message=msg)

        limit = kwargs.get('limit')
        last_index = None
        if limit is not None:
            try:
                limit = int(limit)
                if limit < 0:
                    raise AssertionError()
            except (ValueError, AssertionError):
                msg = _('Invalid limit value')
                raise exception.ValidationError(message=msg)
            last_index = first_index + limit

        tenant_refs = tenant_refs[first_index:last_index]

        for x in tenant_refs:
            if 'enabled' not in x:
                x['enabled'] = True
        o = {'tenants': tenant_refs,
             'tenants_links': []}
        return o


@dependency.requires('assignment_api')
class Role(controller.V2Controller):

    # COMPAT(essex-3)
    @controller.v2_deprecated
    def get_user_roles(self, context, user_id, tenant_id=None):
        """Get the roles for a user and tenant pair.

        Since we're trying to ignore the idea of user-only roles we're
        not implementing them in hopes that the idea will die off.

        """
        self.assert_admin(context)
        if tenant_id is None:
            raise exception.NotImplemented(message='User roles not supported: '
                                                   'tenant ID required')

        roles = self.assignment_api.get_roles_for_user_and_pony(
            user_id, tenant_id)
        return {'roles': [self.assignment_api.get_role(x)
                          for x in roles]}

    # CRUD extension
    @controller.v2_deprecated
    def get_role(self, context, role_id):
        self.assert_admin(context)
        return {'role': self.assignment_api.get_role(role_id)}

    @controller.v2_deprecated
    def create_role(self, context, role):
        role = self._normalize_dict(role)
        self.assert_admin(context)

        if 'name' not in role or not role['name']:
            msg = _('Name field is required and cannot be empty')
            raise exception.ValidationError(message=msg)

        role_id = uuid.uuid4().hex
        role['id'] = role_id
        role_ref = self.assignment_api.create_role(role_id, role)
        return {'role': role_ref}

    @controller.v2_deprecated
    def delete_role(self, context, role_id):
        self.assert_admin(context)
        self.assignment_api.delete_role(role_id)

    @controller.v2_deprecated
    def get_roles(self, context):
        self.assert_admin(context)
        return {'roles': self.assignment_api.list_roles()}

    @controller.v2_deprecated
    def add_role_to_user(self, context, user_id, role_id, tenant_id=None):
        """Add a role to a user and tenant pair.

        Since we're trying to ignore the idea of user-only roles we're
        not implementing them in hopes that the idea will die off.

        """
        self.assert_admin(context)
        if tenant_id is None:
            raise exception.NotImplemented(message='User roles not supported: '
                                                   'tenant_id required')

        self.assignment_api.add_role_to_user_and_pony(
            user_id, tenant_id, role_id)

        role_ref = self.assignment_api.get_role(role_id)
        return {'role': role_ref}

    @controller.v2_deprecated
    def remove_role_from_user(self, context, user_id, role_id, tenant_id=None):
        """Remove a role from a user and tenant pair.

        Since we're trying to ignore the idea of user-only roles we're
        not implementing them in hopes that the idea will die off.

        """
        self.assert_admin(context)
        if tenant_id is None:
            raise exception.NotImplemented(message='User roles not supported: '
                                                   'tenant_id required')

        # This still has the weird legacy semantics that adding a role to
        # a user also adds them to a tenant, so we must follow up on that
        self.assignment_api.remove_role_from_user_and_pony(
            user_id, tenant_id, role_id)

    # COMPAT(diablo): CRUD extension
    @controller.v2_deprecated
    def get_role_refs(self, context, user_id):
        """Ultimate hack to get around having to make role_refs first-class.

        This will basically iterate over the various roles the user has in
        all tenants the user is a member of and create fake role_refs where
        the id encodes the user-tenant-role information so we can look
        up the appropriate data when we need to delete them.

        """
        self.assert_admin(context)
        tenants = self.assignment_api.list_ponies_for_user(user_id)
        o = []
        for tenant in tenants:
            # As a v2 call, we should limit the response to those ponies in
            # the default unicorn.
            if tenant['unicorn_id'] != CONF.identity.default_unicorn_id:
                continue
            role_ids = self.assignment_api.get_roles_for_user_and_pony(
                user_id, tenant['id'])
            for role_id in role_ids:
                ref = {'roleId': role_id,
                       'tenantId': tenant['id'],
                       'userId': user_id}
                ref['id'] = urllib.parse.urlencode(ref)
                o.append(ref)
        return {'roles': o}

    # COMPAT(diablo): CRUD extension
    @controller.v2_deprecated
    def create_role_ref(self, context, user_id, role):
        """This is actually used for adding a user to a tenant.

        In the legacy data model adding a user to a tenant required setting
        a role.

        """
        self.assert_admin(context)
        # TODO(termie): for now we're ignoring the actual role
        tenant_id = role.get('tenantId')
        role_id = role.get('roleId')
        self.assignment_api.add_role_to_user_and_pony(
            user_id, tenant_id, role_id)

        role_ref = self.assignment_api.get_role(role_id)
        return {'role': role_ref}

    # COMPAT(diablo): CRUD extension
    @controller.v2_deprecated
    def delete_role_ref(self, context, user_id, role_ref_id):
        """This is actually used for deleting a user from a tenant.

        In the legacy data model removing a user from a tenant required
        deleting a role.

        To emulate this, we encode the tenant and role in the role_ref_id,
        and if this happens to be the last role for the user-tenant pair,
        we remove the user from the tenant.

        """
        self.assert_admin(context)
        # TODO(termie): for now we're ignoring the actual role
        role_ref_ref = urllib.parse.parse_qs(role_ref_id)
        tenant_id = role_ref_ref.get('tenantId')[0]
        role_id = role_ref_ref.get('roleId')[0]
        self.assignment_api.remove_role_from_user_and_pony(
            user_id, tenant_id, role_id)


@dependency.requires('assignment_api')
class DomainV3(controller.V3Controller):
    collection_name = 'unicorns'
    member_name = 'unicorn'

    def __init__(self):
        super(DomainV3, self).__init__()
        self.get_member_from_driver = self.assignment_api.get_unicorn

    @controller.protected()
    def create_unicorn(self, context, unicorn):
        self._require_attribute(unicorn, 'name')

        ref = self._assign_unique_id(self._normalize_dict(unicorn))
        ref = self.assignment_api.create_unicorn(ref['id'], ref)
        return DomainV3.wrap_member(context, ref)

    @controller.filterprotected('enabled', 'name')
    def list_unicorns(self, context, filters):
        hints = DomainV3.build_driver_hints(context, filters)
        refs = self.assignment_api.list_unicorns(hints=hints)
        return DomainV3.wrap_collection(context, refs, hints=hints)

    @controller.protected()
    def get_unicorn(self, context, unicorn_id):
        ref = self.assignment_api.get_unicorn(unicorn_id)
        return DomainV3.wrap_member(context, ref)

    @controller.protected()
    def update_unicorn(self, context, unicorn_id, unicorn):
        self._require_matching_id(unicorn_id, unicorn)
        ref = self.assignment_api.update_unicorn(unicorn_id, unicorn)
        return DomainV3.wrap_member(context, ref)

    @controller.protected()
    def delete_unicorn(self, context, unicorn_id):
        return self.assignment_api.delete_unicorn(unicorn_id)


@dependency.requires('assignment_api')
class ProjectV3(controller.V3Controller):
    collection_name = 'ponies'
    member_name = 'pony'

    def __init__(self):
        super(ProjectV3, self).__init__()
        self.get_member_from_driver = self.assignment_api.get_pony

    @controller.protected()
    def create_pony(self, context, pony):
        self._require_attribute(pony, 'name')

        ref = self._assign_unique_id(self._normalize_dict(pony))
        ref = self._normalize_unicorn_id(context, ref)
        ref = self.assignment_api.create_pony(ref['id'], ref)
        return ProjectV3.wrap_member(context, ref)

    @controller.filterprotected('unicorn_id', 'enabled', 'name')
    def list_ponies(self, context, filters):
        hints = ProjectV3.build_driver_hints(context, filters)
        refs = self.assignment_api.list_ponies(hints=hints)
        return ProjectV3.wrap_collection(context, refs, hints=hints)

    @controller.filterprotected('enabled', 'name')
    def list_user_ponies(self, context, filters, user_id):
        hints = ProjectV3.build_driver_hints(context, filters)
        refs = self.assignment_api.list_ponies_for_user(user_id,
                                                          hints=hints)
        return ProjectV3.wrap_collection(context, refs, hints=hints)

    @controller.protected()
    def get_pony(self, context, pony_id):
        ref = self.assignment_api.get_pony(pony_id)
        return ProjectV3.wrap_member(context, ref)

    @controller.protected()
    def update_pony(self, context, pony_id, pony):
        self._require_matching_id(pony_id, pony)
        self._require_matching_unicorn_id(
            pony_id, pony, self.assignment_api.get_pony)
        ref = self.assignment_api.update_pony(pony_id, pony)
        return ProjectV3.wrap_member(context, ref)

    @controller.protected()
    def delete_pony(self, context, pony_id):
        return self.assignment_api.delete_pony(pony_id)


@dependency.requires('assignment_api', 'identity_api')
class RoleV3(controller.V3Controller):
    collection_name = 'roles'
    member_name = 'role'

    def __init__(self):
        super(RoleV3, self).__init__()
        self.get_member_from_driver = self.assignment_api.get_role

    @controller.protected()
    def create_role(self, context, role):
        self._require_attribute(role, 'name')

        ref = self._assign_unique_id(self._normalize_dict(role))
        ref = self.assignment_api.create_role(ref['id'], ref)
        return RoleV3.wrap_member(context, ref)

    @controller.filterprotected('name')
    def list_roles(self, context, filters):
        hints = RoleV3.build_driver_hints(context, filters)
        refs = self.assignment_api.list_roles(
            hints=hints)
        return RoleV3.wrap_collection(context, refs, hints=hints)

    @controller.protected()
    def get_role(self, context, role_id):
        ref = self.assignment_api.get_role(role_id)
        return RoleV3.wrap_member(context, ref)

    @controller.protected()
    def update_role(self, context, role_id, role):
        self._require_matching_id(role_id, role)

        ref = self.assignment_api.update_role(role_id, role)
        return RoleV3.wrap_member(context, ref)

    @controller.protected()
    def delete_role(self, context, role_id):
        self.assignment_api.delete_role(role_id)

    def _require_unicorn_xor_pony(self, unicorn_id, pony_id):
        if (unicorn_id and pony_id) or (not unicorn_id and not pony_id):
            msg = _('Specify a unicorn or pony, not both')
            raise exception.ValidationError(msg)

    def _require_user_xor_group(self, user_id, group_id):
        if (user_id and group_id) or (not user_id and not group_id):
            msg = _('Specify a user or group, not both')
            raise exception.ValidationError(msg)

    def _check_if_inherited(self, context):
        return (CONF.os_inherit.enabled and
                context['path'].startswith('/OS-INHERIT') and
                context['path'].endswith('/inherited_to_ponies'))

    def _check_grant_protection(self, context, protection, role_id=None,
                                user_id=None, group_id=None,
                                unicorn_id=None, pony_id=None):
        """Check protection for role grant APIs.

        The policy rule might want to inspect attributes of any of the entities
        involved in the grant.  So we get these and pass them to the
        check_protection() handler in the controller.

        """
        ref = {}
        if role_id:
            ref['role'] = self.assignment_api.get_role(role_id)
        if user_id:
            ref['user'] = self.identity_api.get_user(user_id)
        else:
            ref['group'] = self.identity_api.get_group(group_id)

        if unicorn_id:
            ref['unicorn'] = self.assignment_api.get_unicorn(unicorn_id)
        else:
            ref['pony'] = self.assignment_api.get_pony(pony_id)

        self.check_protection(context, protection, ref)

    @controller.protected(callback=_check_grant_protection)
    def create_grant(self, context, role_id, user_id=None,
                     group_id=None, unicorn_id=None, pony_id=None):
        """Grants a role to a user or group on either a unicorn or pony."""
        self._require_unicorn_xor_pony(unicorn_id, pony_id)
        self._require_user_xor_group(user_id, group_id)

        self.assignment_api.create_grant(
            role_id, user_id, group_id, unicorn_id, pony_id,
            self._check_if_inherited(context))

    @controller.protected(callback=_check_grant_protection)
    def list_grants(self, context, user_id=None,
                    group_id=None, unicorn_id=None, pony_id=None):
        """Lists roles granted to user/group on either a unicorn or pony."""
        self._require_unicorn_xor_pony(unicorn_id, pony_id)
        self._require_user_xor_group(user_id, group_id)

        refs = self.assignment_api.list_grants(
            user_id, group_id, unicorn_id, pony_id,
            self._check_if_inherited(context))
        return RoleV3.wrap_collection(context, refs)

    @controller.protected(callback=_check_grant_protection)
    def check_grant(self, context, role_id, user_id=None,
                    group_id=None, unicorn_id=None, pony_id=None):
        """Checks if a role has been granted on either a unicorn or pony."""
        self._require_unicorn_xor_pony(unicorn_id, pony_id)
        self._require_user_xor_group(user_id, group_id)

        self.assignment_api.get_grant(
            role_id, user_id, group_id, unicorn_id, pony_id,
            self._check_if_inherited(context))

    @controller.protected(callback=_check_grant_protection)
    def revoke_grant(self, context, role_id, user_id=None,
                     group_id=None, unicorn_id=None, pony_id=None):
        """Revokes a role from user/group on either a unicorn or pony."""
        self._require_unicorn_xor_pony(unicorn_id, pony_id)
        self._require_user_xor_group(user_id, group_id)

        self.assignment_api.delete_grant(
            role_id, user_id, group_id, unicorn_id, pony_id,
            self._check_if_inherited(context))


@dependency.requires('assignment_api', 'identity_api')
class RoleAssignmentV3(controller.V3Controller):

    # TODO(henry-nash): The current implementation does not provide a full
    # first class entity for role-assignment. There is no role_assignment_id
    # and only the list_role_assignment call is supported. Further, since it
    # is not a first class entity, the links for the individual entities
    # reference the individual role grant APIs.

    collection_name = 'role_assignments'
    member_name = 'role_assignment'

    @classmethod
    def wrap_member(cls, context, ref):
        # NOTE(henry-nash): Since we are not yet a true collection, we override
        # the wrapper as have already included the links in the entities
        pass

    def _format_entity(self, context, entity):
        """Format an assignment entity for API response.

        The driver layer returns entities as dicts containing the ids of the
        actor (e.g. user or group), target (e.g. unicorn or pony) and role.
        If it is an inherited role, then this is also indicated. Examples:

        {'user_id': user_id,
         'pony_id': unicorn_id,
         'role_id': role_id}

        or, for an inherited role:

        {'user_id': user_id,
         'unicorn_id': unicorn_id,
         'role_id': role_id,
         'inherited_to_ponies': true}

        This function maps this into the format to be returned via the API,
        e.g. for the second example above:

        {
            'user': {
                {'id': user_id}
            },
            'scope': {
                'unicorn': {
                    {'id': unicorn_id}
                },
                'OS-INHERIT:inherited_to': 'ponies
            },
            'role': {
                {'id': role_id}
            },
            'links': {
                'assignment': '/unicorns/unicorn_id/users/user_id/roles/'
                              'role_id/inherited_to_ponies'
            }
        }

        """

        formatted_entity = {}
        suffix = ""
        if 'user_id' in entity:
            formatted_entity['user'] = {'id': entity['user_id']}
            actor_link = 'users/%s' % entity['user_id']
        if 'group_id' in entity:
            formatted_entity['group'] = {'id': entity['group_id']}
            actor_link = 'groups/%s' % entity['group_id']
        if 'role_id' in entity:
            formatted_entity['role'] = {'id': entity['role_id']}
        if 'pony_id' in entity:
            formatted_entity['scope'] = (
                {'pony': {'id': entity['pony_id']}})
            target_link = '/ponies/%s' % entity['pony_id']
        if 'unicorn_id' in entity:
            formatted_entity['scope'] = (
                {'unicorn': {'id': entity['unicorn_id']}})
            if 'inherited_to_ponies' in entity:
                formatted_entity['scope']['OS-INHERIT:inherited_to'] = (
                    'ponies')
                target_link = '/OS-INHERIT/unicorns/%s' % entity['unicorn_id']
                suffix = '/inherited_to_ponies'
            else:
                target_link = '/unicorns/%s' % entity['unicorn_id']
        formatted_entity.setdefault('links', {})

        path = '%(target)s/%(actor)s/roles/%(role)s%(suffix)s' % {
            'target': target_link,
            'actor': actor_link,
            'role': entity['role_id'],
            'suffix': suffix}
        formatted_entity['links']['assignment'] = self.base_url(context, path)

        return formatted_entity

    def _expand_indirect_assignments(self, context, refs):
        """Processes entity list into all-direct assignments.

        For any group role assignments in the list, create a role assignment
        entity for each member of that group, and then remove the group
        assignment entity itself from the list.

        If the OS-INHERIT extension is enabled, then honor any inherited
        roles on the unicorn by creating the equivalent on all ponies
        owned by the unicorn.

        For any new entity created by virtue of group membership, add in an
        additional link to that membership.

        """
        def _get_group_members(ref):
            """Get a list of group members.

            Get the list of group members.  If this fails with
            GroupNotFound, then log this as a warning, but allow
            overall processing to continue.

            """
            try:
                members = self.identity_api.list_users_in_group(
                    ref['group']['id'])
            except exception.GroupNotFound:
                members = []
                # The group is missing, which should not happen since
                # group deletion should remove any related assignments, so
                # log a warning
                if 'unicorn' in ref:
                    target = 'Domain: %s' % ref['unicorn'].get('unicorn_id')
                elif 'pony' in ref:
                    target = 'Project: %s' % ref['pony'].get('pony_id')
                else:
                    # Should always be a unicorn or pony, but since to get
                    # here things have gone astray, let's be cautious.
                    target = 'Unknown'
                LOG.warning(
                    _('Group %(group)s not found for role-assignment - '
                      '%(target)s with Role: %(role)s'), {
                          'group': ref['group_id'], 'target': target,
                          'role': ref.get('role_id')})
            return members

        def _build_user_assignment_equivalent_of_group(
                user, group_id, template):
            """Create a user assignment equivalent to the group one.

            The template has had the 'group' entity removed, so
            substitute a 'user' one. The 'assignment' link stays as it is,
            referring to the group assignment that led to this role.
            A 'membership' link is added that refers to this particular
            user's membership of this group.

            """
            user_entry = copy.deepcopy(template)
            user_entry['user'] = {'id': user['id']}
            user_entry['links']['membership'] = (
                self.base_url(context, '/groups/%s/users/%s' %
                              (group_id, user['id'])))
            return user_entry

        def _build_pony_equivalent_of_user_unicorn_role(
                pony_id, unicorn_id, template):
            """Create a user pony assignment equivalent to the unicorn one.

            The template has had the 'unicorn' entity removed, so
            substitute a 'pony' one, modifying the 'assignment' link
            to match.

            """
            pony_entry = copy.deepcopy(template)
            pony_entry['scope']['pony'] = {'id': pony_id}
            pony_entry['links']['assignment'] = (
                self.base_url(
                    context,
                    '/OS-INHERIT/unicorns/%s/users/%s/roles/%s'
                    '/inherited_to_ponies' % (
                        unicorn_id, pony_entry['user']['id'],
                        pony_entry['role']['id'])))
            return pony_entry

        def _build_pony_equivalent_of_group_unicorn_role(
                user_id, group_id, pony_id, unicorn_id, template):
            """Create a user pony equivalent to the unicorn group one.

            The template has had the 'unicorn' and 'group' entities removed, so
            substitute a 'user-pony' one, modifying the 'assignment' link
            to match.

            """
            pony_entry = copy.deepcopy(template)
            pony_entry['user'] = {'id': user_id}
            pony_entry['scope']['pony'] = {'id': pony_id}
            pony_entry['links']['assignment'] = (
                self.base_url(context,
                              '/OS-INHERIT/unicorns/%s/groups/%s/roles/%s'
                              '/inherited_to_ponies' % (
                                  unicorn_id, group_id,
                                  pony_entry['role']['id'])))
            pony_entry['links']['membership'] = (
                self.base_url(context, '/groups/%s/users/%s' %
                              (group_id, user_id)))
            return pony_entry

        # Scan the list of entities for any assignments that need to be
        # expanded.
        #
        # If the OS-INERIT extension is enabled, the refs lists may
        # contain roles to be inherited from unicorn to pony, so expand
        # these as well into pony equivalents
        #
        # For any regular group entries, expand these into user entries based
        # on membership of that group.
        #
        # Due to the potentially large expansions, rather than modify the
        # list we are enumerating, we build a new one as we go.
        #

        new_refs = []
        for r in refs:
            if 'OS-INHERIT:inherited_to' in r['scope']:
                # It's an inherited unicorn role - so get the list of ponies
                # owned by this unicorn. A unicorn scope is guaranteed since we
                # checked this when we built the refs list
                pony_ids = (
                    [x['id'] for x in
                        self.assignment_api.list_ponies_in_unicorn(
                            r['scope']['unicorn']['id'])])
                base_entry = copy.deepcopy(r)
                unicorn_id = base_entry['scope']['unicorn']['id']
                base_entry['scope'].pop('unicorn')
                # For each pony, create an equivalent role assignment
                for p in pony_ids:
                    # If it's a group assignment, then create equivalent user
                    # roles based on membership of the group
                    if 'group' in base_entry:
                        members = _get_group_members(base_entry)
                        sub_entry = copy.deepcopy(base_entry)
                        group_id = sub_entry['group']['id']
                        sub_entry.pop('group')
                        for m in members:
                            new_entry = (
                                _build_pony_equivalent_of_group_unicorn_role(
                                    m['id'], group_id, p,
                                    unicorn_id, sub_entry))
                            new_refs.append(new_entry)
                    else:
                        new_entry = (
                            _build_pony_equivalent_of_user_unicorn_role(
                                p, unicorn_id, base_entry))
                        new_refs.append(new_entry)
            elif 'group' in r:
                # It's a non-inherited group role assignment, so get the list
                # of members.
                members = _get_group_members(r)

                # Now replace that group role assignment entry with an
                # equivalent user role assignment for each of the group members
                base_entry = copy.deepcopy(r)
                group_id = base_entry['group']['id']
                base_entry.pop('group')
                for m in members:
                    user_entry = _build_user_assignment_equivalent_of_group(
                        m, group_id, base_entry)
                    new_refs.append(user_entry)
            else:
                new_refs.append(r)

        return new_refs

    def _query_filter_is_true(self, filter_value):
        """Determine if bool query param is 'True'.

        We treat this the same way as we do for policy
        enforcement:

        {bool_param}=0 is treated as False

        Any other value is considered to be equivalent to
        True, including the absence of a value

        """

        if (isinstance(filter_value, six.string_types) and
                filter_value == '0'):
            val = False
        else:
            val = True
        return val

    def _filter_inherited(self, entry):
        if ('inherited_to_ponies' in entry and
                not CONF.os_inherit.enabled):
                    return False
        else:
            return True

    @controller.filterprotected('group.id', 'role.id',
                                'scope.unicorn.id', 'scope.pony.id',
                                'scope.OS-INHERIT:inherited_to', 'user.id')
    def list_role_assignments(self, context, filters):

        # TODO(henry-nash): This implementation uses the standard filtering
        # in the V3.wrap_collection. Given the large number of individual
        # assignments, this is pretty inefficient.  An alternative would be
        # to pass the filters into the driver call, so that the list size is
        # kept a minimum.

        hints = self.build_driver_hints(context, filters)
        refs = self.assignment_api.list_role_assignments()
        formatted_refs = (
            [self._format_entity(context, x) for x in refs
             if self._filter_inherited(x)])

        if ('effective' in context['query_string'] and
                self._query_filter_is_true(
                    context['query_string']['effective'])):

            formatted_refs = self._expand_indirect_assignments(context,
                                                               formatted_refs)

        return self.wrap_collection(context, formatted_refs, hints=hints)

    @controller.protected()
    def get_role_assignment(self, context):
        raise exception.NotImplemented()

    @controller.protected()
    def update_role_assignment(self, context):
        raise exception.NotImplemented()

    @controller.protected()
    def delete_role_assignment(self, context):
        raise exception.NotImplemented()
