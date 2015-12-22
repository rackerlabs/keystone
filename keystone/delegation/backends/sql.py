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

import datetime
import six
import uuid

from keystone.common import config
from keystone.common import sql
from keystone.delegation import core

CONF = config.CONF


def expiration_value():
    ttl = CONF.delegation.expiration
    if ttl:
        return datetime.datetime.now() + ttl
    else:
        return None


class DelegationModel(sql.ModelBase, sql.DictBase):
    """Unified delegation model

    'trustor_id': the user considered the source of delegated rights
    'impersonation': allowance for the delegate to impersonate the trustor
    'origins': ancestry chain of delegations
    'ancestors': ancestry chain of trustors
    'strict': whether to check if trustors are all enabled
    'transitive': indicates that rights can be delegated further
    'active': delegated rights can be used by the delegate
    'user_id': delegate user id empowered by the delegation
    'group_id': delegate group id which members are empowered by the delegation
    'project_id': scope of the delegation - the object of rights passed
    'domain_id': scope of the delegation - the object of rights passed
    'deleted_at': timestamp of delegation revocation
    'expires_at': timestamp of delegation expiration
    'remaining_uses': backwards compatibility field
    'inherited_to_projects': delegation applies to inherited projects
    """

    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'impersonation',
                  'user_chain',
                  'delegation_chain',
                  'strict_ancestry',
                  'sealed',
                  'executable',
                  'inherited_to_projects',
                  'user_id',
                  'group_id',
                  'project_id',
                  'domain_id',
                  'deleted_at',
                  'expires_at',
                  'remaining_uses'
                  ]

    id = sql.Column(sql.String(64), primary_key=True,
                    default=lambda: uuid.uuid4().hex)

    # Identification
    trustor_id = sql.Column(sql.String(64), nullable=False)
    impersonation = sql.Column(sql.Boolean, nullable=False, default=False)
    user_chain = sql.Column(sql.MaterializedPathType, nullable=False,
                            default=[])
    delegation_chain = sql.Column(sql.MaterializedPathType, nullable=False,
                                  default=[])
    # Constraints
    strict_ancestry = sql.Column(sql.Boolean, nullable=False, default=False)
    sealed = sql.Column(sql.Boolean, nullable=False, default=True)
    executable = sql.Column(sql.Boolean, nullable=False, default=True)
    inherited_to_projects = sql.Column(sql.Boolean, nullable=False,
                                       default=False)

    # Scope
    user_id = sql.Column(sql.String(64))
    group_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    domain_id = sql.Column(sql.String(64))

    # Timestamps
    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(sql.DateTime, default=expiration_value)

    # Specific fields, may be moved to "extra" blob
    remaining_uses = sql.Column(sql.Integer)

    def inherit(self, agent_id, **kwargs):
        params = self.to_dict()
        params.update(user_chain=self.user_chain + [agent_id],
                      delegation_chain=self.delegation_chain + [self.id],
                      )
        params.update(kwargs)
        inherited = type(self)(**params)
        return inherited

    def scope(self, user_id=None, group_id=None, impersonation=False,
              project_id=None, domain_id=None):
        # TODO(amakarov): XOR user, group
        self.user_id = user_id
        self.group_id = group_id
        self.impersonation = impersonation

        # TODO(amakarov): XOR project, domain
        self.project_id = project_id
        self.domain_id = domain_id

        return self


class RoleDelegationModel(sql.DictBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['delegation_id', 'role_id']

    delegation_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), nullable=False)

    __table_args__ = (sql.PrimaryKeyConstraint('delegation_id', 'role_id'), )


class Driver(core.DelegationDriverV8):

    def derive_delegation(self, id, base_delegation,
                          agent, user, group, impersonation,
                          roles, project, domain, inherited_to_projects,
                          strict_ancestry, sealed, executable):
        session = sql.get_session()
        try:
            if isinstance(base_delegation, DelegationModel):
                base = base_delegation
            elif isinstance(base_delegation, six.text_type):
                base = session.query(DelegationModel).get(base_delegation)
            else:
                raise sql.NotFound()
            # TODO(amakarov): check sealed flag
            # check roles subset
            trustor_id = base['trustor_id']
            user_chain = base['user_chain'] + [agent]
            delegation_chain = base['delegation_chain'] + base['id']
        except sql.NotFound:
            # TODO(amakarov): check available delegations
            trustor_id = agent
            user_chain = [agent]
            delegation_chain = []

        new_delegation_ref = {
            'id': id,
            'trustor_id': trustor_id,
            'impersonation': impersonation,
            'user_chain': user_chain,
            'delegation_chain': delegation_chain,
            'strict_ancestry': strict_ancestry,
            'sealed': sealed,
            'executable': executable,
            'inherited_to_projects': inherited_to_projects,
            'user_id': user,
            'group_id': group,
            'project_id': project,
            'domain_id': domain,
            'deleted_at': None,
            'expires_at': datetime.datetime.now() + datetime.timedelta(
                CONF.delegation.expiration),
            'remaining_uses': 1
        }
        delegation = DelegationModel.from_dict(new_delegation_ref)
        with session.begin():
            session.add(delegation)
            for role in roles:
                session.add(RoleDelegationModel(delegation_id=id,
                                                role_id=role))

    def update_delegation(self, delegation, grant_roles, revoke_roles):
        pass

    def revoke_delegation(self, delegation):
        session = sql.get_session()
        with session.begin():
            (session.query(DelegationModel).filter(id=delegation)
             .update(deleted_at=datetime.now()))

    def list_delegations(self, hints, user, group, project, domain, role,
                         expanded=False):
        pass

    def get_delegation(self, delegation):

        session = sql.get_session()
        delegation = (session.query(DelegationModel)
                      .options(sql.joinedload(RoleDelegationModel.role_id))
                      .get(delegation))
        delegation_ref = delegation.to_dict()
        return delegation_ref
