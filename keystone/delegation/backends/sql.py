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
import uuid

from keystone.common import config
from keystone.common import sql

CONF = config.CONF


def expiration_value():
    ttl = CONF.delegation.expiration
    if ttl:
        return datetime.datetime.now() + datetime.timedelta(ttl)
    else:
        return None


class RoleDelegationModel(sql.ModelBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['id', 'delegation_id', 'role_id']

    id = sql.Column(sql.String(64), nullable=False, primary_key=True,
                    default=lambda: uuid.uuid4().hex)
    delegation_id = sql.Column(
        sql.String(64),
        sql.ForeignKey('delegation.id',
                       ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False)
    role_id = sql.Column(
        sql.String(64),
        sql.ForeignKey('role.id',
                       ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False)

    __table_args__ = (sql.UniqueConstraint('role_id', 'delegation_id',
                      name='duplicate_role_delegation_constraint'),)


class DelegationModel(sql.ModelBase, sql.DictBase):
    """Unified delegation model

    'trustor_id': the user considered the source of delegated rights
    'agent_id': the creator user of the delegation
    'impersonation': allowance for the delegate to impersonate the trustor
    'redelegated_id': parent link to track delegation ancestry chain
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
    'redelegation_count': number of times the delegation can be redelegated
    """

    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'agent_id',
                  'redelegated_id',
                  'impersonation',
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
                  'remaining_uses',
                  'redelegation_count'
                  ]

    id = sql.Column(sql.String(64), primary_key=True,
                    default=lambda: uuid.uuid4().hex)

    # Identification
    trustor_id = sql.Column(sql.String(64), nullable=False)
    agent_id = sql.Column(sql.String(64), nullable=False)
    impersonation = sql.Column(sql.Boolean, nullable=False, default=False)
    redelegated_id = sql.Column(sql.String(64), nullable=True)

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
    redelegation_count = sql.Column(sql.Integer)

    extra = sql.Column(sql.JsonBlob())

    __table_args__ = (sql.UniqueConstraint(
                      'trustor_id', 'user_id', 'project_id',
                      'impersonation', 'expires_at',
                      name='duplicate_trust_delegation_constraint'),)
