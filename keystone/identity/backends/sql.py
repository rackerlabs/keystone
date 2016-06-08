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

from oslo_config import cfg
import sqlalchemy

from keystone.common import driver_hints
from keystone.common import sql
from keystone.common import utils
from keystone import exception
from keystone.i18n import _
from keystone.identity.backends import base
from keystone.identity.backends import sql_model as model


CONF = cfg.CONF


class Identity(base.IdentityDriverV8):
    # NOTE(henry-nash): Override the __init__() method so as to take a
    # config parameter to enable sql to be used as a domain-specific driver.
    def __init__(self, conf=None):
        self.conf = conf
        super(Identity, self).__init__()

    @property
    def is_sql(self):
        return True

    def authenticate(self, user_id, password):
        return Authenticator().authenticate(user_id, password)

    @sql.handle_conflicts(conflict_type='user')
    def create_user(self, user_id, user):
        user = utils.hash_user_password(user)
        with sql.session_for_write() as session:
            user_ref = model.User.from_dict(user)
            session.add(user_ref)
            return base.filter_user(user_ref.to_dict())

    @driver_hints.truncated
    def list_users(self, hints):
        with sql.session_for_read() as session:
            query = session.query(model.User).outerjoin(model.LocalUser)
            user_refs = sql.filter_limit_query(model.User, query, hints)
            return [base.filter_user(x.to_dict()) for x in user_refs]

    def _get_user(self, session, user_id):
        user_ref = session.query(model.User).get(user_id)
        if not user_ref:
            raise exception.UserNotFound(user_id=user_id)
        return user_ref

    def get_user(self, user_id):
        with sql.session_for_read() as session:
            return base.filter_user(
                self._get_user(session, user_id).to_dict())

    def get_user_by_name(self, user_name, domain_id):
        with sql.session_for_read() as session:
            query = session.query(model.User).join(model.LocalUser)
            query = query.filter(sqlalchemy.and_(
                model.LocalUser.name == user_name,
                model.LocalUser.domain_id == domain_id))
            try:
                user_ref = query.one()
            except sql.NotFound:
                raise exception.UserNotFound(user_id=user_name)
            return base.filter_user(user_ref.to_dict())

    @sql.handle_conflicts(conflict_type='user')
    def update_user(self, user_id, user):
        with sql.session_for_write() as session:
            user_ref = self._get_user(session, user_id)
            if user.get('password') is not None:
                PasswordHistoryValidator().validate(user['password'], user_ref)
            old_user_dict = user_ref.to_dict()
            user = utils.hash_user_password(user)
            for k in user:
                old_user_dict[k] = user[k]
            new_user = model.User.from_dict(old_user_dict)
            for attr in model.User.attributes:
                if attr != 'id' and attr not in model.User.readonly_attributes:
                    setattr(user_ref, attr, getattr(new_user, attr))
            user_ref.extra = new_user.extra
            return base.filter_user(
                user_ref.to_dict(include_extra_dict=True))

    def add_user_to_group(self, user_id, group_id):
        with sql.session_for_write() as session:
            self.get_group(group_id)
            self.get_user(user_id)
            query = session.query(model.UserGroupMembership)
            query = query.filter_by(user_id=user_id)
            query = query.filter_by(group_id=group_id)
            rv = query.first()
            if rv:
                return

            session.add(model.UserGroupMembership(user_id=user_id,
                                                  group_id=group_id))

    def check_user_in_group(self, user_id, group_id):
        with sql.session_for_read() as session:
            self.get_group(group_id)
            self.get_user(user_id)
            query = session.query(model.UserGroupMembership)
            query = query.filter_by(user_id=user_id)
            query = query.filter_by(group_id=group_id)
            if not query.first():
                raise exception.NotFound(_("User '%(user_id)s' not found in"
                                           " group '%(group_id)s'") %
                                         {'user_id': user_id,
                                          'group_id': group_id})

    def remove_user_from_group(self, user_id, group_id):
        # We don't check if user or group are still valid and let the remove
        # be tried anyway - in case this is some kind of clean-up operation
        with sql.session_for_write() as session:
            query = session.query(model.UserGroupMembership)
            query = query.filter_by(user_id=user_id)
            query = query.filter_by(group_id=group_id)
            membership_ref = query.first()
            if membership_ref is None:
                # Check if the group and user exist to return descriptive
                # exceptions.
                self.get_group(group_id)
                self.get_user(user_id)
                raise exception.NotFound(_("User '%(user_id)s' not found in"
                                           " group '%(group_id)s'") %
                                         {'user_id': user_id,
                                          'group_id': group_id})
            session.delete(membership_ref)

    def list_groups_for_user(self, user_id, hints):
        with sql.session_for_read() as session:
            self.get_user(user_id)
            query = session.query(model.Group).join(model.UserGroupMembership)
            query = query.filter(model.UserGroupMembership.user_id == user_id)
            query = sql.filter_limit_query(model.Group, query, hints)
            return [g.to_dict() for g in query]

    def list_users_in_group(self, group_id, hints):
        with sql.session_for_read() as session:
            self.get_group(group_id)
            query = session.query(model.User).outerjoin(model.LocalUser)
            query = query.join(model.UserGroupMembership)
            query = query.filter(
                model.UserGroupMembership.group_id == group_id)
            query = sql.filter_limit_query(model.User, query, hints)
            return [base.filter_user(u.to_dict()) for u in query]

    def delete_user(self, user_id):
        with sql.session_for_write() as session:
            ref = self._get_user(session, user_id)

            q = session.query(model.UserGroupMembership)
            q = q.filter_by(user_id=user_id)
            q.delete(False)

            session.delete(ref)

    # group crud

    @sql.handle_conflicts(conflict_type='group')
    def create_group(self, group_id, group):
        with sql.session_for_write() as session:
            ref = model.Group.from_dict(group)
            session.add(ref)
            return ref.to_dict()

    @driver_hints.truncated
    def list_groups(self, hints):
        with sql.session_for_read() as session:
            query = session.query(model.Group)
            refs = sql.filter_limit_query(model.Group, query, hints)
            return [ref.to_dict() for ref in refs]

    def _get_group(self, session, group_id):
        ref = session.query(model.Group).get(group_id)
        if not ref:
            raise exception.GroupNotFound(group_id=group_id)
        return ref

    def get_group(self, group_id):
        with sql.session_for_read() as session:
            return self._get_group(session, group_id).to_dict()

    def get_group_by_name(self, group_name, domain_id):
        with sql.session_for_read() as session:
            query = session.query(model.Group)
            query = query.filter_by(name=group_name)
            query = query.filter_by(domain_id=domain_id)
            try:
                group_ref = query.one()
            except sql.NotFound:
                raise exception.GroupNotFound(group_id=group_name)
            return group_ref.to_dict()

    @sql.handle_conflicts(conflict_type='group')
    def update_group(self, group_id, group):
        with sql.session_for_write() as session:
            ref = self._get_group(session, group_id)
            old_dict = ref.to_dict()
            for k in group:
                old_dict[k] = group[k]
            new_group = model.Group.from_dict(old_dict)
            for attr in model.Group.attributes:
                if attr != 'id':
                    setattr(ref, attr, getattr(new_group, attr))
            ref.extra = new_group.extra
            return ref.to_dict()

    def delete_group(self, group_id):
        with sql.session_for_write() as session:
            ref = self._get_group(session, group_id)

            q = session.query(model.UserGroupMembership)
            q = q.filter_by(group_id=group_id)
            q.delete(False)

            session.delete(ref)


class Authenticator(object):
    def authenticate(self, user_id, password):
        with sql.session_for_read() as session:
            user_ref = None
            try:
                user_ref = self._get_user(session, user_id)
                # TODO(rderose): handle if password.created_at is not set,
                # fallout from rolling upgrade
            except exception.UserNotFound:
                raise AssertionError(_('Invalid user / password'))
            if not utils.check_password(password, user_ref.password):
                raise AssertionError(_('Invalid user / password'))
            elif self._is_user_disabled(user_ref):
                raise exception.UserDisabled(user_id=user_id)
            elif self._is_password_expired(user_ref.password_expires_at):
                raise exception.PasswordExpired(user_id=user_id)
            self._set_last_auth_at(user_ref['id'])
            return base.filter_user(user_ref.to_dict())

    def _get_user(self, session, user_id):
        user_ref = session.query(model.User).get(user_id)
        if not user_ref:
            raise exception.UserNotFound(user_id=user_id)
        return user_ref

    def _is_password_expired(self, expires_at):
        if expires_at:
            return datetime.datetime.utcnow() >= expires_at
        return False

    def _is_user_disabled(self, user_ref):
        max_days_inactive = (
            CONF.security_compliance.disable_user_account_days_inactive)
        if user_ref.last_auth_at and max_days_inactive > 0:
            days_inactive = (
                (datetime.datetime.utcnow() - user_ref.last_auth_at).days
            )
            if days_inactive >= max_days_inactive:
                self._disable_user(user_ref['id'])
                return True
        return (user_ref.enabled is not None if
                not user_ref.enabled else False)

    def _disable_user(self, user_id):
        with sql.session_for_write() as session:
            query = session.query(model.User)
            query = query.filter(model.User.id == user_id)
            query.update({'enabled': False})
            return

    def _set_last_auth_at(self, user_id):
        with sql.session_for_write() as session:
            query = session.query(model.User).join(model.LocalUser)
            query = query.filter(model.User.id == user_id)
            query.update({'last_auth_at': datetime.datetime.now()})
            return


class PasswordHistoryValidator(object):
    def validate(self, password, user_ref):
        cnt = 0
        max_cnt = (CONF.security_compliance.unique_last_password_count if
                   CONF.security_compliance.unique_last_password_count else 0)
        passwords = sorted(user_ref.local_user.passwords,
                           key=lambda x: x.created_at, reverse=True)
        for password_ref in passwords:
            if cnt >= max_cnt:
                break
            elif utils.check_password(password, password_ref.password):
                detail = _('Invalid password: matches value in history')
                raise exception.PasswordValidationError(detail=detail)
            cnt = cnt + 1
