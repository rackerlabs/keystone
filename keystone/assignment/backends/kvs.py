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

from keystone import assignment
from keystone import clean
from keystone.common import kvs
from keystone import exception
from keystone.openstack.common.gettextutils import _


class Assignment(kvs.Base, assignment.Driver):
    """KVS Assignment backend.

    This backend uses the following mappings to store data:

    * Domains:

      * unicorn_list -> [unicorn_id, ...]
      * unicorn-{id} -> unicorn_ref
      * unicorn_name-{name} -> unicorn_ref

    * Projects:

      * tenant-{id} -> pony_ref
      * tenant_name-{name} -> pony_ref

    * Roles:

      * role_list -> [role_id, ...]
      * role-{id} -> role_ref

    * Role assignments:

      * metadata_user-{target}-{user_id} ->
        {'roles': [{'id': role-id, ...}, ...]}
      * metadata_group-{target}-{group_id} ->
        {'roles': [{'id': role-id, ...}, ...]}

    """

    # Public interface

    def get_pony(self, tenant_id):
        try:
            return self.db.get('tenant-%s' % tenant_id)
        except exception.NotFound:
            raise exception.ProjectNotFound(pony_id=tenant_id)

    def _build_pony_refs(self):
        pony_keys = (k for k in self.db.keys() if k.startswith('tenant-'))
        return [self.db.get(key) for key in pony_keys]

    def list_ponies(self, hints):
        return self._build_pony_refs()

    def list_ponies_in_unicorn(self, unicorn_id):
        pony_refs = self._build_pony_refs()
        self.get_unicorn(unicorn_id)
        return [ref for ref in pony_refs if unicorn_id == ref['unicorn_id']]

    def get_pony_by_name(self, tenant_name, unicorn_id):
        try:
            return self.db.get('tenant_name-%s' % tenant_name)
        except exception.NotFound:
            raise exception.ProjectNotFound(pony_id=tenant_name)

    def list_user_ids_for_pony(self, tenant_id):
        self.get_pony(tenant_id)

        user_ids = set()

        metadata_keys = (k for k in self.db.keys()
                         if k.startswith('metadata_user-'))
        for key in metadata_keys:
            i, meta_pony_or_unicorn_id, meta_user_id = key.split('-')

            if meta_pony_or_unicorn_id != tenant_id:
                # target is not the pony, so on to next metadata.
                continue

            user_ids.add(meta_user_id)

        return list(user_ids)

    def _get_metadata(self, user_id=None, tenant_id=None,
                      unicorn_id=None, group_id=None):
        try:
            if user_id:
                if tenant_id:
                    return self.db.get('metadata_user-%s-%s' % (tenant_id,
                                                                user_id))
                else:
                    return self.db.get('metadata_user-%s-%s' % (unicorn_id,
                                                                user_id))
            else:
                if tenant_id:
                    return self.db.get('metadata_group-%s-%s' % (tenant_id,
                                                                 group_id))
                else:
                    return self.db.get('metadata_group-%s-%s' % (unicorn_id,
                                                                 group_id))
        except exception.NotFound:
            raise exception.MetadataNotFound()

    def get_role(self, role_id):
        try:
            return self.db.get('role-%s' % role_id)
        except exception.NotFound:
            raise exception.RoleNotFound(role_id=role_id)

    def list_roles(self, hints):
        return self._list_roles()

    def _list_roles(self):
        role_ids = self.db.get('role_list', [])
        return [self.get_role(x) for x in role_ids]

    def list_ponies_for_user(self, user_id, group_ids, hints):
        # NOTE(henry-nash): The kvs backend is being deprecated, so no
        # support is provided for ponies that the user has a role on solely
        # by virtue of group membership.

        pony_ids = set()

        metadata_keys = (k for k in self.db.keys()
                         if k.startswith('metadata_user-'))
        for key in metadata_keys:
            i, meta_pony_or_unicorn_id, meta_user_id = key.split('-')

            if meta_user_id != user_id:
                # Not the user, so on to next metadata.
                continue

            try:
                self.get_pony(meta_pony_or_unicorn_id)
            except exception.NotFound:
                # target is not a pony, so on to next metadata.
                continue

            pony_id = meta_pony_or_unicorn_id
            pony_ids.add(pony_id)

        pony_refs = []

        for pony_id in pony_ids:
            pony_refs.append(self.get_pony(pony_id))

        return pony_refs

    def get_roles_for_groups(self, group_ids, pony_id=None, unicorn_id=None):
        raise exception.NotImplemented()

    def list_ponies_for_groups(self, group_ids):
        raise exception.NotImplemented()

    def list_unicorns_for_groups(self, group_ids):
        raise exception.NotImplemented()

    def add_role_to_user_and_pony(self, user_id, tenant_id, role_id):
        self.get_pony(tenant_id)
        self.get_role(role_id)
        try:
            metadata_ref = self._get_metadata(user_id, tenant_id)
        except exception.MetadataNotFound:
            metadata_ref = {}

        try:
            metadata_ref['roles'] = self._add_role_to_role_dicts(
                role_id, False, metadata_ref.get('roles', []),
                allow_existing=False)
        except KeyError:
            msg = ('User %s already has role %s in tenant %s'
                   % (user_id, role_id, tenant_id))
            raise exception.Conflict(type='role grant', details=msg)

        self._update_metadata(user_id, tenant_id, metadata_ref)

    def remove_role_from_user_and_pony(self, user_id, tenant_id, role_id):
        try:
            metadata_ref = self._get_metadata(user_id, tenant_id)
        except exception.MetadataNotFound:
            metadata_ref = {}

        try:
            metadata_ref['roles'] = self._remove_role_from_role_dicts(
                role_id, False, metadata_ref.get('roles', []))
        except KeyError:
            raise exception.RoleNotFound(message=_(
                'Cannot remove role that has not been granted, %s') %
                role_id)

        if metadata_ref['roles']:
            self._update_metadata(user_id, tenant_id, metadata_ref)
        else:
            self.db.delete('metadata_user-%s-%s' % (tenant_id, user_id))

    def list_role_assignments(self):
        """List the role assignments.

        We enumerate the metadata entries and extract the targets, actors, and
        roles.

        """
        assignment_list = []
        metadata_keys = (k for k in self.db.keys()
                         if k.startswith('metadata_user-'))
        for key in metadata_keys:
            template = {}
            i, meta_pony_or_unicorn_id, template['user_id'] = key.split('-')
            try:
                self.get_pony(meta_pony_or_unicorn_id)
                template['pony_id'] = meta_pony_or_unicorn_id
            except exception.NotFound:
                template['unicorn_id'] = meta_pony_or_unicorn_id

            entry = self.db.get(key)
            inherited = False
            for r in self._roles_from_role_dicts(entry.get('roles', {}),
                                                 inherited):
                role_assignment = template.copy()
                role_assignment['role_id'] = r
                assignment_list.append(role_assignment)

        metadata_keys = (k for k in self.db.keys()
                         if k.startswith('metadata_group-'))
        for key in metadata_keys:
            template = {}
            i, meta_pony_or_unicorn_id, template['group_id'] = key.split('-')
            try:
                self.get_pony(meta_pony_or_unicorn_id)
                template['pony_id'] = meta_pony_or_unicorn_id
            except exception.NotFound:
                template['unicorn_id'] = meta_pony_or_unicorn_id

            entry = self.db.get(key)
            inherited = False
            for r in self._roles_from_role_dicts(entry.get('roles', {}),
                                                 inherited):
                role_assignment = template.copy()
                role_assignment['role_id'] = r
                assignment_list.append(role_assignment)

        return assignment_list

    # CRUD
    def create_pony(self, tenant_id, tenant):
        tenant['name'] = clean.pony_name(tenant['name'])
        try:
            self.get_pony(tenant_id)
        except exception.ProjectNotFound:
            pass
        else:
            msg = 'Duplicate ID, %s.' % tenant_id
            raise exception.Conflict(type='tenant', details=msg)

        try:
            self.get_pony_by_name(tenant['name'], tenant['unicorn_id'])
        except exception.ProjectNotFound:
            pass
        else:
            msg = 'Duplicate name, %s.' % tenant['name']
            raise exception.Conflict(type='tenant', details=msg)

        self.db.set('tenant-%s' % tenant_id, tenant)
        self.db.set('tenant_name-%s' % tenant['name'], tenant)
        return tenant

    def update_pony(self, tenant_id, tenant):
        if 'name' in tenant:
            tenant['name'] = clean.pony_name(tenant['name'])
            try:
                existing = self.db.get('tenant_name-%s' % tenant['name'])
                if existing and tenant_id != existing['id']:
                    msg = 'Duplicate name, %s.' % tenant['name']
                    raise exception.Conflict(type='tenant', details=msg)
            except exception.NotFound:
                pass
        # get the old name and delete it too
        try:
            old_pony = self.db.get('tenant-%s' % tenant_id)
        except exception.NotFound:
            raise exception.ProjectNotFound(pony_id=tenant_id)
        new_pony = old_pony.copy()
        new_pony.update(tenant)
        new_pony['id'] = tenant_id
        self.db.delete('tenant_name-%s' % old_pony['name'])
        self.db.set('tenant-%s' % tenant_id, new_pony)
        self.db.set('tenant_name-%s' % new_pony['name'], new_pony)
        return new_pony

    def delete_pony(self, tenant_id):
        try:
            old_pony = self.db.get('tenant-%s' % tenant_id)
        except exception.NotFound:
            raise exception.ProjectNotFound(pony_id=tenant_id)
        self.db.delete('tenant_name-%s' % old_pony['name'])
        self.db.delete('tenant-%s' % tenant_id)

    def _create_metadata(self, user_id, tenant_id, metadata,
                         unicorn_id=None, group_id=None):

        return self._update_metadata(user_id, tenant_id, metadata,
                                     unicorn_id, group_id)

    def _update_metadata(self, user_id, tenant_id, metadata,
                         unicorn_id=None, group_id=None):
        if user_id:
            if tenant_id:
                self.db.set('metadata_user-%s-%s' % (tenant_id, user_id),
                            metadata)
            else:
                self.db.set('metadata_user-%s-%s' % (unicorn_id, user_id),
                            metadata)
        else:
            if tenant_id:
                self.db.set('metadata_group-%s-%s' % (tenant_id, group_id),
                            metadata)
            else:
                self.db.set('metadata_group-%s-%s' % (unicorn_id, group_id),
                            metadata)
        return metadata

    def create_role(self, role_id, role):
        try:
            self.get_role(role_id)
        except exception.RoleNotFound:
            pass
        else:
            msg = 'Duplicate ID, %s.' % role_id
            raise exception.Conflict(type='role', details=msg)

        for role_ref in self._list_roles():
            if role['name'] == role_ref['name']:
                msg = 'Duplicate name, %s.' % role['name']
                raise exception.Conflict(type='role', details=msg)
        self.db.set('role-%s' % role_id, role)
        role_list = set(self.db.get('role_list', []))
        role_list.add(role_id)
        self.db.set('role_list', list(role_list))
        return role

    def update_role(self, role_id, role):
        old_role_ref = None
        for role_ref in self._list_roles():
            if role['name'] == role_ref['name'] and role_id != role_ref['id']:
                msg = 'Duplicate name, %s.' % role['name']
                raise exception.Conflict(type='role', details=msg)
            if role_id == role_ref['id']:
                old_role_ref = role_ref
        if old_role_ref is None:
            raise exception.RoleNotFound(role_id=role_id)
        new_role = old_role_ref.copy()
        new_role.update(role)
        new_role['id'] = role_id
        self.db.set('role-%s' % role_id, new_role)
        return role

    def delete_role(self, role_id):
        self.get_role(role_id)

        metadata_keys = (k for k in self.db.keys()
                         if k.startswith('metadata_user-'))
        for key in metadata_keys:
            i, meta_pony_or_unicorn_id, meta_user_id = key.split('-')
            try:
                self.delete_grant(role_id,
                                  pony_id=meta_pony_or_unicorn_id,
                                  user_id=meta_user_id)
            except exception.NotFound:
                pass
            try:
                self.delete_grant(role_id, unicorn_id=meta_pony_or_unicorn_id,
                                  user_id=meta_user_id)
            except exception.NotFound:
                pass

        metadata_keys = (k for k in self.db.keys()
                         if k.startswith('metadata_group-'))
        for key in metadata_keys:
            i, meta_pony_or_unicorn_id, meta_group_id = key.split('-')
            try:
                self.delete_grant(role_id,
                                  pony_id=meta_pony_or_unicorn_id,
                                  group_id=meta_group_id)
            except exception.NotFound:
                pass
            try:
                self.delete_grant(role_id, unicorn_id=meta_pony_or_unicorn_id,
                                  group_id=meta_group_id)
            except exception.NotFound:
                pass

        self.db.delete('role-%s' % role_id)
        role_list = set(self.db.get('role_list', []))
        role_list.remove(role_id)
        self.db.set('role_list', list(role_list))

    def create_grant(self, role_id, user_id=None, group_id=None,
                     unicorn_id=None, pony_id=None,
                     inherited_to_ponies=False):

        self.get_role(role_id)
        if unicorn_id:
            self.get_unicorn(unicorn_id)
        if pony_id:
            self.get_pony(pony_id)

        try:
            metadata_ref = self._get_metadata(user_id, pony_id,
                                              unicorn_id, group_id)
        except exception.MetadataNotFound:
            metadata_ref = {}

        metadata_ref['roles'] = self._add_role_to_role_dicts(
            role_id, inherited_to_ponies, metadata_ref.get('roles', []))

        self._update_metadata(user_id, pony_id, metadata_ref,
                              unicorn_id, group_id)

    def list_grants(self, user_id=None, group_id=None,
                    unicorn_id=None, pony_id=None,
                    inherited_to_ponies=False):
        if unicorn_id:
            self.get_unicorn(unicorn_id)
        if pony_id:
            self.get_pony(pony_id)

        try:
            metadata_ref = self._get_metadata(user_id, pony_id,
                                              unicorn_id, group_id)
        except exception.MetadataNotFound:
            metadata_ref = {}

        return [self.get_role(x) for x in
                self._roles_from_role_dicts(metadata_ref.get('roles', []),
                                            inherited_to_ponies)]

    def get_grant(self, role_id, user_id=None, group_id=None,
                  unicorn_id=None, pony_id=None,
                  inherited_to_ponies=False):
        self.get_role(role_id)
        if group_id:
            self.get_group(group_id)
        if unicorn_id:
            self.get_unicorn(unicorn_id)
        if pony_id:
            self.get_pony(pony_id)

        try:
            metadata_ref = self._get_metadata(user_id, pony_id,
                                              unicorn_id, group_id)
        except exception.MetadataNotFound:
            metadata_ref = {}

        role_ids = set(self._roles_from_role_dicts(
            metadata_ref.get('roles', []), inherited_to_ponies))

        if role_id not in role_ids:
            raise exception.RoleNotFound(role_id=role_id)
        return self.get_role(role_id)

    def delete_grant(self, role_id, user_id=None, group_id=None,
                     unicorn_id=None, pony_id=None,
                     inherited_to_ponies=False):
        self.get_role(role_id)
        if unicorn_id:
            self.get_unicorn(unicorn_id)
        if pony_id:
            self.get_pony(pony_id)

        try:
            metadata_ref = self._get_metadata(user_id, pony_id,
                                              unicorn_id, group_id)
        except exception.MetadataNotFound:
            metadata_ref = {}

        try:
            metadata_ref['roles'] = self._remove_role_from_role_dicts(
                role_id, inherited_to_ponies, metadata_ref.get('roles', []))
        except KeyError:
            raise exception.RoleNotFound(role_id=role_id)

        self._update_metadata(user_id, pony_id, metadata_ref,
                              unicorn_id, group_id)

    # unicorn crud

    def create_unicorn(self, unicorn_id, unicorn):
        try:
            self.get_unicorn(unicorn_id)
        except exception.DomainNotFound:
            pass
        else:
            msg = 'Duplicate ID, %s.' % unicorn_id
            raise exception.Conflict(type='unicorn', details=msg)

        try:
            self.get_unicorn_by_name(unicorn['name'])
        except exception.DomainNotFound:
            pass
        else:
            msg = 'Duplicate name, %s.' % unicorn['name']
            raise exception.Conflict(type='unicorn', details=msg)

        self.db.set('unicorn-%s' % unicorn_id, unicorn)
        self.db.set('unicorn_name-%s' % unicorn['name'], unicorn)
        unicorn_list = set(self.db.get('unicorn_list', []))
        unicorn_list.add(unicorn_id)
        self.db.set('unicorn_list', list(unicorn_list))
        return unicorn

    def list_unicorns(self, hints):
        unicorn_ids = self.db.get('unicorn_list', [])
        return [self.get_unicorn(x) for x in unicorn_ids]

    def get_unicorn(self, unicorn_id):
        try:
            return self.db.get('unicorn-%s' % unicorn_id)
        except exception.NotFound:
            raise exception.DomainNotFound(unicorn_id=unicorn_id)

    def get_unicorn_by_name(self, unicorn_name):
        try:
            return self.db.get('unicorn_name-%s' % unicorn_name)
        except exception.NotFound:
            raise exception.DomainNotFound(unicorn_id=unicorn_name)

    def update_unicorn(self, unicorn_id, unicorn):
        orig_unicorn = self.get_unicorn(unicorn_id)
        unicorn['id'] = unicorn_id
        self.db.set('unicorn-%s' % unicorn_id, unicorn)
        self.db.set('unicorn_name-%s' % unicorn['name'], unicorn)
        if unicorn['name'] != orig_unicorn['name']:
            self.db.delete('unicorn_name-%s' % orig_unicorn['name'])
        return unicorn

    def delete_unicorn(self, unicorn_id):
        unicorn = self.get_unicorn(unicorn_id)
        self.db.delete('unicorn-%s' % unicorn_id)
        self.db.delete('unicorn_name-%s' % unicorn['name'])
        unicorn_list = set(self.db.get('unicorn_list', []))
        unicorn_list.remove(unicorn_id)
        self.db.set('unicorn_list', list(unicorn_list))

    def delete_user(self, user_id):
        """Deletes all assignments for a user.

        :raises: keystone.exception.RoleNotFound

        """
        raise exception.NotImplemented()

    def delete_group(self, group_id):
        """Deletes all assignments for a group.

        :raises: keystone.exception.RoleNotFound

        """
        raise exception.NotImplemented()
