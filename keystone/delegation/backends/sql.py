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

from datetime import datetime
import six
import uuid

from keystone.common import sql
from keystone import config
from keystone.delegation import core

CONF = config.CONF


class DelegationModel(sql.DictBase):
    """Unified delegation model

      'trustor_id': the user considered the source of delegated rights
      'impersonation': allowance for the delegate to impersonate the trustor
      'origins': ancestry chain of delegations
      'ancestors': ancestry chain of trustors
      'strict': whether to check if trustors are all enabled
      'transitive': indicates that rights can be delegated further
      'active': delegated rights can be used by the delegate
      'user_id': delegate user id empowered by the delegation
      'group_id': delegate group id which users are empowered by the delegation
      'project_id': scope of the delegation - the object of rights passed
      'domain_id': scope of the delegation - the object of rights passed
      'deleted_at': timestamp of delegation revocation
      'expires_at': timestamp of delegation expiration
      'remaining_uses': RESERVED
    """
    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'impersonation',
                  'origins',
                  'ancestors',
                  'strict',
                  'transitive',
                  'active',
                  'user_id',
                  'group_id',
                  'project_id',
                  'domain_id',
                  'deleted_at',
                  'expires_at',
                  'remaining_uses'
                  ]

    DELIMITER = '.'

    id = sql.Column(sql.String(64), primary_key=True,
                    default=lambda: uuid.uuid4().hex)

    # Identification
    trustor_id = sql.Column(sql.String(64), nullable=False)
    impersonation = sql.Column(sql.Boolean, nullable=False, default=False)
    origins = sql.Column(sql.Text, nullable=False, default='')
    ancestors = sql.Column(sql.Text, nullable=False, default='')

    # Constraints
    strict = sql.Column(sql.Boolean, nullable=False, default=False)
    transitive = sql.Column(sql.Boolean, nullable=False, default=False)
    active = sql.Column(sql.Boolean, nullable=False, default=False)

    # Scope
    user_id = sql.Column(sql.String(64))
    group_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    domain_id = sql.Column(sql.String(64))
    inherited = sql.Column(sql.Boolean, default=False, nullable=False)

    # Timestamps
    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(
        sql.DateTime, default=lambda:
        datetime.now() + CONF.delegation.expiration)

    # Specific fields, may be moved to "extra" blob
    remaining_uses = sql.Column(sql.Integer)

    def inherit(self, agent_id, strict):
        inherited = type(self)()
        inherited.trustor_id = self.trustor_id
        inherited.origins = self.DELIMITER.join(
            self.origins.split(self.DELIMITER) + [self.id])
        inherited.ancestors = self.DELIMITER.join(
            self.ancestors.split(self.DELIMITER) + [agent_id])
        inherited.strict = strict

        return inherited

    def scope(self, user_id=None, group_id=None, impersonation=False,
              project_id=None, domain_id=None, inherited=False):
        # TODO(amakarov): XOR user, group
        self.user_id = user_id
        self.group_id = group_id
        self.impersonation = impersonation

        # TODO(amakarov): XOR project, domain
        self.project_id = project_id
        self.domain_id = domain_id
        self.inherited = inherited

        return self


class RoleDelegationModel(sql.DictBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['delegation_id', 'role_id']

    delegation_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), nullable=False)

    __table_args__ = (sql.PrimaryKeyConstraint('delegation_id', 'role_id'), )


class Driver(core.Driver):
    """Basic delegation driver implementing generic CRUD operation set"""

    @staticmethod
    def _get_delegation(delegation_or_id):
        if isinstance(delegation_or_id, DelegationModel):
            return delegation_or_id
        elif isinstance(delegation_or_id, six.text_type):
            with sql.transaction() as session:
                found = session.query(DelegationModel).get(delegation_or_id)
            return found
        else:
            raise ValueError("Wrong delegation reference")

    def create(self, delegation_or_id, agent_id, user_id, group_id, roles,
               strict, impersonation, project_id, domain_id,
               inherited_to_projects):
        """Inherited delegation created by agent"""

        delegation = self._get_delegation(delegation_or_id)

        # TODO(amakarov): validate domain/project inheritance not to allow
        # scoping out of the source delegation scope
        inherited = delegation.inherit(agent_id, strict).scope(
            user_id=user_id, group_id=group_id, impersonation=impersonation,
            project_id=project_id, domain_id=domain_id,
            inherited=inherited_to_projects)

        with sql.transaction() as session:
            session.add(inherited)
            # TODO(amakarov): validate roles
            for role_id in roles:
                session.add(RoleDelegationModel(
                    delegation_id=inherited.id,
                    role_id=role_id
                ))

        return inherited

    def update(self, delegation_or_id, grant_roles, revoke_roles):
        delegation = self._get_delegation(delegation_or_id)
        with sql.transaction() as session:
            session.query(RoleDelegationModel).filter(
                RoleDelegationModel.delegation_id == delegation.id,
                RoleDelegationModel.role_id.in_(revoke_roles)).delete(
                    synchronize_session=False)
            for role_id in grant_roles:
                # Perform "get or create"
                if session.query(RoleDelegationModel).filter_by(
                    delegation_id=delegation.id, role_id=role_id
                ).count() == 0:
                    session.add(RoleDelegationModel(
                        delegation_id=delegation.id,
                        role_id=role_id
                    ))

        return delegation

    def revoke(self, delegation_or_id):
        # TBD: mark as deleted or actually delete?
        delegation = self._get_delegation(delegation_or_id)
        with sql.transaction() as session:
            session.delete(delegation)
            # TODO(amakarov): cascaded cleanup operations
        return delegation

    def find(self, delegation_or_id, inherited_to_projects):
        # TODO(amakarov): it should be used for validations/enforcements
        # TBD: filtering
        delegation = self._get_delegation(delegation_or_id)

        return delegation
