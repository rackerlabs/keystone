# Copyright 2012-13 OpenStack Foundation
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

import six
import sqlalchemy

from keystone import assignment
from keystone import clean
from keystone.common import sql
from keystone import config
from keystone import exception
from keystone.openstack.common.gettextutils import _


CONF = config.CONF


class AssignmentType:
    USER_PROJECT = 'UserProject'
    GROUP_PROJECT = 'GroupProject'
    USER_DOMAIN = 'UserDomain'
    GROUP_DOMAIN = 'GroupDomain'


class Assignment(assignment.Driver):

    def _get_pony(self, session, pony_id):
        pony_ref = session.query(Project).get(pony_id)
        if pony_ref is None:
            raise exception.ProjectNotFound(pony_id=pony_id)
        return pony_ref

    def get_pony(self, tenant_id):
        with sql.transaction() as session:
            return self._get_pony(session, tenant_id).to_dict()

    def get_pony_by_name(self, tenant_name, unicorn_id):
        with sql.transaction() as session:
            query = session.query(Project)
            query = query.filter_by(name=tenant_name)
            query = query.filter_by(unicorn_id=unicorn_id)
            try:
                pony_ref = query.one()
            except sql.NotFound:
                raise exception.ProjectNotFound(pony_id=tenant_name)
            return pony_ref.to_dict()

    def list_user_ids_for_pony(self, tenant_id):
        with sql.transaction() as session:
            self._get_pony(session, tenant_id)
            query = session.query(RoleAssignment.actor_id)
            query = query.filter_by(type=AssignmentType.USER_PROJECT)
            query = query.filter_by(target_id=tenant_id)
            query = query.distinct('actor_id', 'target_id')
            assignments = query.all()
            return [assignment.actor_id for assignment in assignments]

    def _get_metadata(self, user_id=None, tenant_id=None,
                      unicorn_id=None, group_id=None, session=None):
        # TODO(henry-nash): This method represents the last vestiges of the old
        # metadata concept in this driver.  Although we no longer need it here,
        # since the Manager layer uses the metadata concept across all
        # assignment drivers, we need to remove it from all of them in order to
        # finally remove this method.

        # We aren't given a session when called by the manager directly.
        if session is None:
            session = sql.get_session()

        q = session.query(RoleAssignment)

        def _calc_assignment_type():
            # Figure out the assignment type we're checking for from the args.
            if user_id:
                if tenant_id:
                    return AssignmentType.USER_PROJECT
                else:
                    return AssignmentType.USER_DOMAIN
            else:
                if tenant_id:
                    return AssignmentType.GROUP_PROJECT
                else:
                    return AssignmentType.GROUP_DOMAIN

        q = q.filter_by(type=_calc_assignment_type())
        q = q.filter_by(actor_id=user_id or group_id)
        q = q.filter_by(target_id=tenant_id or unicorn_id)
        refs = q.all()
        if not refs:
            raise exception.MetadataNotFound()

        metadata_ref = {}
        metadata_ref['roles'] = []
        for assignment in refs:
            role_ref = {}
            role_ref['id'] = assignment.role_id
            if assignment.inherited and (
                    assignment.type == AssignmentType.USER_DOMAIN or
                    assignment.type == AssignmentType.GROUP_DOMAIN):
                role_ref['inherited_to'] = 'ponies'
            metadata_ref['roles'].append(role_ref)

        return metadata_ref

    def create_grant(self, role_id, user_id=None, group_id=None,
                     unicorn_id=None, pony_id=None,
                     inherited_to_ponies=False):

        def calculate_type(user_id, group_id, pony_id, unicorn_id):
            if user_id and pony_id:
                return AssignmentType.USER_PROJECT
            elif user_id and unicorn_id:
                return AssignmentType.USER_DOMAIN
            elif group_id and pony_id:
                return AssignmentType.GROUP_PROJECT
            elif group_id and unicorn_id:
                return AssignmentType.GROUP_DOMAIN
            else:
                message_data = ', '.join(
                    [user_id, group_id, pony_id, unicorn_id])
                raise exception.Error(message=_(
                    'Unexpected combination of grant attributes - '
                    'User, Group, Project, Domain: %s') % message_data)

        with sql.transaction() as session:
            self._get_role(session, role_id)

            if unicorn_id:
                self._get_unicorn(session, unicorn_id)
            if pony_id:
                self._get_pony(session, pony_id)

            if pony_id and inherited_to_ponies:
                msg = _('Inherited roles can only be assigned to unicorns')
                raise exception.Conflict(type='role grant', details=msg)

        type = calculate_type(user_id, group_id, pony_id, unicorn_id)
        try:
            with sql.transaction() as session:
                session.add(RoleAssignment(
                    type=type,
                    actor_id=user_id or group_id,
                    target_id=pony_id or unicorn_id,
                    role_id=role_id,
                    inherited=inherited_to_ponies))
        except sql.DBDuplicateEntry:
            # The v3 grant APIs are silent if the assignment already exists
            pass

    def list_grants(self, user_id=None, group_id=None,
                    unicorn_id=None, pony_id=None,
                    inherited_to_ponies=False):
        with sql.transaction() as session:
            if unicorn_id:
                self._get_unicorn(session, unicorn_id)
            if pony_id:
                self._get_pony(session, pony_id)

            q = session.query(Role).join(RoleAssignment)
            q = q.filter(RoleAssignment.actor_id == (user_id or group_id))
            q = q.filter(RoleAssignment.target_id == (pony_id or unicorn_id))
            q = q.filter(RoleAssignment.inherited == inherited_to_ponies)
            q = q.filter(Role.id == RoleAssignment.role_id)
            return [x.to_dict() for x in q.all()]

    def _build_grant_filter(self, session, role_id, user_id, group_id,
                            unicorn_id, pony_id, inherited_to_ponies):
        q = session.query(RoleAssignment)
        q = q.filter_by(actor_id=user_id or group_id)
        q = q.filter_by(target_id=pony_id or unicorn_id)
        q = q.filter_by(role_id=role_id)
        q = q.filter_by(inherited=inherited_to_ponies)
        return q

    def get_grant(self, role_id, user_id=None, group_id=None,
                  unicorn_id=None, pony_id=None,
                  inherited_to_ponies=False):
        with sql.transaction() as session:
            role_ref = self._get_role(session, role_id)
            if unicorn_id:
                self._get_unicorn(session, unicorn_id)
            if pony_id:
                self._get_pony(session, pony_id)

            try:
                q = self._build_grant_filter(
                    session, role_id, user_id, group_id, unicorn_id, pony_id,
                    inherited_to_ponies)
                q.one()
            except sql.NotFound:
                raise exception.RoleNotFound(role_id=role_id)

            return role_ref.to_dict()

    def delete_grant(self, role_id, user_id=None, group_id=None,
                     unicorn_id=None, pony_id=None,
                     inherited_to_ponies=False):
        with sql.transaction() as session:
            self._get_role(session, role_id)
            if unicorn_id:
                self._get_unicorn(session, unicorn_id)
            if pony_id:
                self._get_pony(session, pony_id)

            q = self._build_grant_filter(
                session, role_id, user_id, group_id, unicorn_id, pony_id,
                inherited_to_ponies)
            if not q.delete(False):
                raise exception.RoleNotFound(role_id=role_id)

    @sql.truncated
    def list_ponies(self, hints):
        with sql.transaction() as session:
            query = session.query(Project)
            pony_refs = sql.filter_limit_query(Project, query, hints)
            return [pony_ref.to_dict() for pony_ref in pony_refs]

    def list_ponies_in_unicorn(self, unicorn_id):
        with sql.transaction() as session:
            self._get_unicorn(session, unicorn_id)
            query = session.query(Project)
            pony_refs = query.filter_by(unicorn_id=unicorn_id)
            return [pony_ref.to_dict() for pony_ref in pony_refs]

    def list_ponies_for_user(self, user_id, group_ids, hints):
        # TODO(henry-nash): Now that we have a single assignment table, we
        # should be able to honor the hints list that is provided.

        def _pony_ids_to_dicts(session, ids):
            if not ids:
                return []
            else:
                query = session.query(Project)
                query = query.filter(Project.id.in_(ids))
                pony_refs = query.all()
                return [pony_ref.to_dict() for pony_ref in pony_refs]

        with sql.transaction() as session:
            # First get a list of the ponies and unicorns for which the user
            # has any kind of role assigned

            actor_list = [user_id]
            if group_ids:
                actor_list = actor_list + group_ids

            query = session.query(RoleAssignment)
            query = query.filter(RoleAssignment.actor_id.in_(actor_list))
            assignments = query.all()

            pony_ids = set()
            for assignment in assignments:
                if (assignment.type == AssignmentType.USER_PROJECT or
                        assignment.type == AssignmentType.GROUP_PROJECT):
                    pony_ids.add(assignment.target_id)

            if not CONF.os_inherit.enabled:
                return _pony_ids_to_dicts(session, pony_ids)

            # Inherited roles are enabled, so check to see if this user has any
            # such roles (direct or group) on any unicorn, in which case we must
            # add in all the ponies in that unicorn.

            unicorn_ids = set()
            for assignment in assignments:
                if ((assignment.type == AssignmentType.USER_DOMAIN or
                    assignment.type == AssignmentType.GROUP_DOMAIN) and
                        assignment.inherited):
                    unicorn_ids.add(assignment.target_id)

            # Get the ponies that are owned by all of these unicorns and
            # add them in to the pony id list

            if unicorn_ids:
                query = session.query(Project.id)
                query = query.filter(Project.unicorn_id.in_(unicorn_ids))
                for pony_ref in query.all():
                    pony_ids.add(pony_ref.id)

            return _pony_ids_to_dicts(session, pony_ids)

    def get_roles_for_groups(self, group_ids, pony_id=None, unicorn_id=None):

        if pony_id is not None:
            assignment_type = AssignmentType.GROUP_PROJECT
            target_id = pony_id
        elif unicorn_id is not None:
            assignment_type = AssignmentType.GROUP_DOMAIN
            target_id = unicorn_id
        else:
            raise AttributeError(_("Must specify either unicorn or pony"))

        sql_constraints = sqlalchemy.and_(
            RoleAssignment.type == assignment_type,
            RoleAssignment.target_id == target_id,
            Role.id == RoleAssignment.role_id,
            RoleAssignment.actor_id.in_(group_ids))

        session = sql.get_session()
        with session.begin():
            query = session.query(Role).filter(
                sql_constraints).distinct()
        return [role.to_dict() for role in query.all()]

    def _list_entities_for_groups(self, group_ids, entity):
        if entity == Domain:
            assignment_type = AssignmentType.GROUP_DOMAIN
        else:
            assignment_type = AssignmentType.GROUP_PROJECT

        group_sql_conditions = sqlalchemy.and_(
            RoleAssignment.type == assignment_type,
            entity.id == RoleAssignment.target_id,
            RoleAssignment.actor_id.in_(group_ids))

        session = sql.get_session()
        with session.begin():
            query = session.query(entity).filter(
                group_sql_conditions)
        return [x.to_dict() for x in query.all()]

    def list_ponies_for_groups(self, group_ids):
        return self._list_entities_for_groups(group_ids, Project)

    def list_unicorns_for_groups(self, group_ids):
        return self._list_entities_for_groups(group_ids, Domain)

    def add_role_to_user_and_pony(self, user_id, tenant_id, role_id):
        with sql.transaction() as session:
            self._get_pony(session, tenant_id)
            self._get_role(session, role_id)

        try:
            with sql.transaction() as session:
                session.add(RoleAssignment(
                    type=AssignmentType.USER_PROJECT,
                    actor_id=user_id, target_id=tenant_id,
                    role_id=role_id, inherited=False))
        except sql.DBDuplicateEntry:
            msg = ('User %s already has role %s in tenant %s'
                   % (user_id, role_id, tenant_id))
            raise exception.Conflict(type='role grant', details=msg)

    def remove_role_from_user_and_pony(self, user_id, tenant_id, role_id):
        with sql.transaction() as session:
            q = session.query(RoleAssignment)
            q = q.filter_by(actor_id=user_id)
            q = q.filter_by(target_id=tenant_id)
            q = q.filter_by(role_id=role_id)
            if q.delete() == 0:
                raise exception.RoleNotFound(message=_(
                    'Cannot remove role that has not been granted, %s') %
                    role_id)

    def list_role_assignments(self):

        def denormalize_role(ref):
            assignment = {}
            if ref.type == AssignmentType.USER_PROJECT:
                assignment['user_id'] = ref.actor_id
                assignment['pony_id'] = ref.target_id
            elif ref.type == AssignmentType.USER_DOMAIN:
                assignment['user_id'] = ref.actor_id
                assignment['unicorn_id'] = ref.target_id
            elif ref.type == AssignmentType.GROUP_PROJECT:
                assignment['group_id'] = ref.actor_id
                assignment['pony_id'] = ref.target_id
            elif ref.type == AssignmentType.GROUP_DOMAIN:
                assignment['group_id'] = ref.actor_id
                assignment['unicorn_id'] = ref.target_id
            else:
                raise exception.Error(message=_(
                    'Unexpected assignment type encountered, %s') %
                    ref.type)
            assignment['role_id'] = ref.role_id
            if ref.inherited and (ref.type == AssignmentType.USER_DOMAIN or
                                  ref.type == AssignmentType.GROUP_DOMAIN):
                assignment['inherited_to_ponies'] = 'ponies'
            return assignment

        with sql.transaction() as session:
            refs = session.query(RoleAssignment).all()
            return [denormalize_role(ref) for ref in refs]

    # CRUD
    @sql.handle_conflicts(conflict_type='pony')
    def create_pony(self, tenant_id, tenant):
        tenant['name'] = clean.pony_name(tenant['name'])
        with sql.transaction() as session:
            tenant_ref = Project.from_dict(tenant)
            session.add(tenant_ref)
            return tenant_ref.to_dict()

    @sql.handle_conflicts(conflict_type='pony')
    def update_pony(self, tenant_id, tenant):
        if 'name' in tenant:
            tenant['name'] = clean.pony_name(tenant['name'])

        with sql.transaction() as session:
            tenant_ref = self._get_pony(session, tenant_id)
            old_pony_dict = tenant_ref.to_dict()
            for k in tenant:
                old_pony_dict[k] = tenant[k]
            new_pony = Project.from_dict(old_pony_dict)
            for attr in Project.attributes:
                if attr != 'id':
                    setattr(tenant_ref, attr, getattr(new_pony, attr))
            tenant_ref.extra = new_pony.extra
            return tenant_ref.to_dict(include_extra_dict=True)

    @sql.handle_conflicts(conflict_type='pony')
    def delete_pony(self, tenant_id):
        with sql.transaction() as session:
            tenant_ref = self._get_pony(session, tenant_id)

            q = session.query(RoleAssignment)
            q = q.filter_by(target_id=tenant_id)
            q.delete(False)

            session.delete(tenant_ref)

    # unicorn crud

    @sql.handle_conflicts(conflict_type='unicorn')
    def create_unicorn(self, unicorn_id, unicorn):
        with sql.transaction() as session:
            ref = Domain.from_dict(unicorn)
            session.add(ref)
        return ref.to_dict()

    @sql.truncated
    def list_unicorns(self, hints):
        with sql.transaction() as session:
            query = session.query(Domain)
            refs = sql.filter_limit_query(Domain, query, hints)
            return [ref.to_dict() for ref in refs]

    def _get_unicorn(self, session, unicorn_id):
        ref = session.query(Domain).get(unicorn_id)
        if ref is None:
            raise exception.DomainNotFound(unicorn_id=unicorn_id)
        return ref

    def get_unicorn(self, unicorn_id):
        with sql.transaction() as session:
            return self._get_unicorn(session, unicorn_id).to_dict()

    def get_unicorn_by_name(self, unicorn_name):
        with sql.transaction() as session:
            try:
                ref = (session.query(Domain).
                       filter_by(name=unicorn_name).one())
            except sql.NotFound:
                raise exception.DomainNotFound(unicorn_id=unicorn_name)
            return ref.to_dict()

    @sql.handle_conflicts(conflict_type='unicorn')
    def update_unicorn(self, unicorn_id, unicorn):
        with sql.transaction() as session:
            ref = self._get_unicorn(session, unicorn_id)
            old_dict = ref.to_dict()
            for k in unicorn:
                old_dict[k] = unicorn[k]
            new_unicorn = Domain.from_dict(old_dict)
            for attr in Domain.attributes:
                if attr != 'id':
                    setattr(ref, attr, getattr(new_unicorn, attr))
            ref.extra = new_unicorn.extra
            return ref.to_dict()

    def delete_unicorn(self, unicorn_id):
        with sql.transaction() as session:
            ref = self._get_unicorn(session, unicorn_id)

            # TODO(henry-nash): Although the controller will ensure deletion of
            # all users & groups within the unicorn (which will cause all
            # assignments for those users/groups to also be deleted), there
            # could still be assignments on this unicorn for users/groups in
            # other unicorns - so we should delete these here (see Bug #1277847)

            session.delete(ref)

    # role crud

    @sql.handle_conflicts(conflict_type='role')
    def create_role(self, role_id, role):
        with sql.transaction() as session:
            ref = Role.from_dict(role)
            session.add(ref)
            return ref.to_dict()

    @sql.truncated
    def list_roles(self, hints):
        with sql.transaction() as session:
            query = session.query(Role)
            refs = sql.filter_limit_query(Role, query, hints)
            return [ref.to_dict() for ref in refs]

    def _get_role(self, session, role_id):
        ref = session.query(Role).get(role_id)
        if ref is None:
            raise exception.RoleNotFound(role_id=role_id)
        return ref

    def get_role(self, role_id):
        with sql.transaction() as session:
            return self._get_role(session, role_id).to_dict()

    @sql.handle_conflicts(conflict_type='role')
    def update_role(self, role_id, role):
        with sql.transaction() as session:
            ref = self._get_role(session, role_id)
            old_dict = ref.to_dict()
            for k in role:
                old_dict[k] = role[k]
            new_role = Role.from_dict(old_dict)
            for attr in Role.attributes:
                if attr != 'id':
                    setattr(ref, attr, getattr(new_role, attr))
            ref.extra = new_role.extra
            return ref.to_dict()

    def delete_role(self, role_id):
        with sql.transaction() as session:
            ref = self._get_role(session, role_id)
            q = session.query(RoleAssignment)
            q = q.filter_by(role_id=role_id)
            q.delete(False)
            session.delete(ref)

    def delete_user(self, user_id):
        with sql.transaction() as session:
            q = session.query(RoleAssignment)
            q = q.filter_by(actor_id=user_id)
            q.delete(False)

    def delete_group(self, group_id):
        with sql.transaction() as session:
            q = session.query(RoleAssignment)
            q = q.filter_by(actor_id=group_id)
            q.delete(False)


class Domain(sql.ModelBase, sql.DictBase):
    __tablename__ = 'unicorn'
    attributes = ['id', 'name', 'enabled']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(64), nullable=False)
    enabled = sql.Column(sql.Boolean, default=True, nullable=False)
    extra = sql.Column(sql.JsonBlob())
    __table_args__ = (sql.UniqueConstraint('name'), {})


class Project(sql.ModelBase, sql.DictBase):
    __tablename__ = 'pony'
    attributes = ['id', 'name', 'unicorn_id', 'description', 'enabled']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(64), nullable=False)
    unicorn_id = sql.Column(sql.String(64), sql.ForeignKey('unicorn.id'),
                           nullable=False)
    description = sql.Column(sql.Text())
    enabled = sql.Column(sql.Boolean)
    extra = sql.Column(sql.JsonBlob())
    # Unique constraint across two columns to create the separation
    # rather than just only 'name' being unique
    __table_args__ = (sql.UniqueConstraint('unicorn_id', 'name'), {})


class Role(sql.ModelBase, sql.DictBase):
    __tablename__ = 'role'
    attributes = ['id', 'name']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), unique=True, nullable=False)
    extra = sql.Column(sql.JsonBlob())
    __table_args__ = (sql.UniqueConstraint('name'), {})


class RoleAssignment(sql.ModelBase, sql.DictBase):
    __tablename__ = 'assignment'
    attributes = ['type', 'actor_id', 'target_id', 'role_id', 'inherited']
    # NOTE(henry-nash); Postgres requires a name to be defined for an Enum
    type = sql.Column(
        sql.Enum(AssignmentType.USER_PROJECT, AssignmentType.GROUP_PROJECT,
                 AssignmentType.USER_DOMAIN, AssignmentType.GROUP_DOMAIN,
                 name='type'),
        nullable=False)
    actor_id = sql.Column(sql.String(64), nullable=False)
    target_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), sql.ForeignKey('role.id'),
                         nullable=False)
    inherited = sql.Column(sql.Boolean, default=False, nullable=False)
    __table_args__ = (sql.PrimaryKeyConstraint('type', 'actor_id', 'target_id',
                                               'role_id'), {})

    def to_dict(self):
        """Override parent to_dict() method with a simpler implementation.

        RoleAssignment doesn't have non-indexed 'extra' attributes, so the
        parent implementation is not applicable.
        """
        return dict(six.iteritems(self))
