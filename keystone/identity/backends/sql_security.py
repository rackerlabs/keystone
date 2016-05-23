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
import re

from oslo_config import cfg

from keystone.common import sql
from keystone.common import utils
from keystone import exception
from keystone.i18n import _
from keystone.identity.backends import base
from keystone.identity.backends import sql_model as model


CONF = cfg.CONF


class Authenticator(object):
    def authenticate(self, user_id, password):
        with sql.session_for_read() as session:
            user_ref = None
            try:
                user_ref = self._get_user(session, user_id)
            except exception.UserNotFound:
                raise AssertionError(_('Invalid user / password'))
            if not self._password_matches(password, user_ref.password):
                raise AssertionError(_('Invalid user / password'))
            if self._is_change_password_required(user_ref, password):
                raise exception.ChangePasswordRequired(user_id=user_id)
            return base.filter_user(user_ref.to_dict())

    def _password_matches(self, password, hashed_password):
        """Check the specified password against the data store.

        Note that we'll pass in the entire user_ref in case the subclass
        needs things like user_ref.get('name')
        For further justification, please see the follow up suggestion at
        https://blueprints.launchpad.net/keystone/+spec/sql-identiy-pam

        """
        return utils.check_password(password, hashed_password)

    def _get_user(self, session, user_id):
        user_ref = session.query(model.User).get(user_id)
        if not user_ref:
            raise exception.UserNotFound(user_id=user_id)
        return user_ref

    def _is_change_password_required(self, user_ref, password):
        is_change_password_required = False
        password_ref = self._get_password_ref(user_ref, password)
        if not PasswordValidator().is_valid(password):
            is_change_password_required = True
        elif self._is_password_expired(password_ref.created_at):
            is_change_password_required = True
        return is_change_password_required

    def _get_password_ref(self, user_ref, password):
        for password_ref in user_ref.local_user.passwords:
            if self._password_matches(password, password_ref.password):
                return password_ref
        return None

    def _is_password_expired(self, created_at):
        # TODO(rderose) if not created_at, update created_at date for user...
        expires_days = CONF.security_compliance.password_expires_days
        if expires_days and expires_days > 0:
            now = datetime.datetime.utcnow()
            expired_date = (created_at + datetime.timedelta(days=expires_days))
            if now >= expired_date:
                return True
        return False


class PasswordValidator(object):
    def is_valid(self, password):
        pattern = CONF.security_compliance.password_regex
        if pattern:
            return re.match(pattern, password)
        return True


class PasswordSaver(object):
    pass
