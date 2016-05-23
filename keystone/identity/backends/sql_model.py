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
import sqlalchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import orm

from oslo_config import cfg
from oslo_log import log

from keystone.common import sql
from keystone.i18n import _LW


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class User(sql.ModelBase, sql.DictBase):
    __tablename__ = 'user'
    attributes = ['id', 'name', 'domain_id', 'password', 'enabled',
                  'default_project_id', 'password_expires_at']
    readonly_attributes = ['password_expires_at']
    id = sql.Column(sql.String(64), primary_key=True)
    enabled = sql.Column(sql.Boolean)
    extra = sql.Column(sql.JsonBlob())
    default_project_id = sql.Column(sql.String(64))
    local_user = orm.relationship('LocalUser', uselist=False,
                                  single_parent=True, lazy='subquery',
                                  cascade='all,delete-orphan', backref='user')
    federated_users = orm.relationship('FederatedUser',
                                       single_parent=True,
                                       lazy='subquery',
                                       cascade='all,delete-orphan',
                                       backref='user')

    # name property
    @hybrid_property
    def name(self):
        if self.local_user:
            return self.local_user.name
        elif self.federated_users:
            return self.federated_users[0].display_name
        else:
            return None

    @name.setter
    def name(self, value):
        if not self.local_user:
            self.local_user = LocalUser()
        self.local_user.name = value

    @name.expression
    def name(cls):
        return LocalUser.name

    # password properties
    @hybrid_property
    def password_ref(self):
        if self.local_user and self.local_user.passwords:
            for password_ref in self.local_user.passwords:
                if not password_ref.expired:
                    return password_ref
        return None

    @hybrid_property
    def password_expires_at(self):
        return PasswordExpiresAtGetter().get_expires_at(self.id,
                                                        self.password_ref)

    @hybrid_property
    def password(self):
        if self.password_ref:
            return self.password_ref.password
        return None

    @password.setter
    def password(self, value):
        if not self.local_user:
            self.local_user = LocalUser()
        for password_ref in self.local_user.passwords:
            password_ref.expired = True
        if value:
            new_password_ref = Password()
            new_password_ref.password = value
            new_password_ref.created_at = datetime.datetime.utcnow()
            new_password_ref.expired = False
            self.local_user.passwords.append(new_password_ref)

    @password.expression
    def password(cls):
        return Password.password

    # domain_id property
    @hybrid_property
    def domain_id(self):
        if self.local_user:
            return self.local_user.domain_id
        else:
            return None

    @domain_id.setter
    def domain_id(self, value):
        if not self.local_user:
            self.local_user = LocalUser()
        self.local_user.domain_id = value

    @domain_id.expression
    def domain_id(cls):
        return LocalUser.domain_id

    def to_dict(self, include_extra_dict=False):
        d = super(User, self).to_dict(include_extra_dict=include_extra_dict)
        if 'default_project_id' in d and d['default_project_id'] is None:
            del d['default_project_id']
        return d

    @classmethod
    def from_dict(cls, user_dict):
        for attribute in cls.readonly_attributes:
            if attribute in user_dict:
                del user_dict[attribute]
        return super(User, cls).from_dict(user_dict)


class LocalUser(sql.ModelBase, sql.DictBase):
    __tablename__ = 'local_user'
    attributes = ['id', 'user_id', 'domain_id', 'name']
    id = sql.Column(sql.Integer, primary_key=True)
    user_id = sql.Column(sql.String(64), sql.ForeignKey('user.id',
                         ondelete='CASCADE'), unique=True)
    domain_id = sql.Column(sql.String(64), nullable=False)
    name = sql.Column(sql.String(255), nullable=False)
    passwords = orm.relationship('Password', single_parent=True,
                                 cascade='all,delete-orphan',
                                 backref='local_user')
    __table_args__ = (sql.UniqueConstraint('domain_id', 'name'), {})


class Password(sql.ModelBase, sql.DictBase):
    __tablename__ = 'password'
    attributes = ['id', 'local_user_id', 'password', 'created_at',
                  'expired']
    id = sql.Column(sql.Integer, primary_key=True)
    local_user_id = sql.Column(sql.Integer, sql.ForeignKey('local_user.id',
                               ondelete='CASCADE'))
    password = sql.Column(sql.String(128))
    created_at = sql.Column(sql.DateTime, nullable=False,
                            default=datetime.datetime.utcnow)
    expired = sql.Column(sql.Boolean, default=False)


class FederatedUser(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'federated_user'
    attributes = ['id', 'user_id', 'idp_id', 'protocol_id', 'unique_id',
                  'display_name']
    id = sql.Column(sql.Integer, primary_key=True)
    user_id = sql.Column(sql.String(64), sql.ForeignKey('user.id',
                                                        ondelete='CASCADE'))
    idp_id = sql.Column(sql.String(64), sql.ForeignKey('identity_provider.id',
                                                       ondelete='CASCADE'))
    protocol_id = sql.Column(sql.String(64), nullable=False)
    unique_id = sql.Column(sql.String(255), nullable=False)
    display_name = sql.Column(sql.String(255), nullable=True)
    __table_args__ = (
        sql.UniqueConstraint('idp_id', 'protocol_id', 'unique_id'),
        sqlalchemy.ForeignKeyConstraint(['protocol_id', 'idp_id'],
                                        ['federation_protocol.id',
                                         'federation_protocol.idp_id'])
    )


class Group(sql.ModelBase, sql.DictBase):
    __tablename__ = 'group'
    attributes = ['id', 'name', 'domain_id', 'description']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(64), nullable=False)
    domain_id = sql.Column(sql.String(64), nullable=False)
    description = sql.Column(sql.Text())
    extra = sql.Column(sql.JsonBlob())
    # Unique constraint across two columns to create the separation
    # rather than just only 'name' being unique
    __table_args__ = (sql.UniqueConstraint('domain_id', 'name'),)


class UserGroupMembership(sql.ModelBase, sql.DictBase):
    """Group membership join table."""

    __tablename__ = 'user_group_membership'
    user_id = sql.Column(sql.String(64),
                         sql.ForeignKey('user.id'),
                         primary_key=True)
    group_id = sql.Column(sql.String(64),
                          sql.ForeignKey('group.id'),
                          primary_key=True)


class PasswordExpiresAtGetter(object):
    def get_expires_at(self, user_id, password_ref):
        if password_ref and not self._is_in_ignore_list(user_id):
            expires_days = CONF.security_compliance.password_expires_days
            if expires_days and expires_days > 0:
                expired_date = (
                    password_ref.created_at +
                    datetime.timedelta(days=expires_days)
                )
                return expired_date.replace(microsecond=0)
        return None

    def _is_in_ignore_list(self, user_id):
        ignore_str = CONF.security_compliance.password_expires_ignore_list
        if ignore_str:
            try:
                ignore_list = ignore_str.split(',')
                return user_id in ignore_list
            except Exception:
                LOG.warning(
                    _LW('Invalid config setting: '
                        'security_compliance.password_expires_ignore_list'))
        return False
