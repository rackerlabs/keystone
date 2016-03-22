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

import uuid

import ldap3
from oslo_config import cfg
from oslo_log import log
from oslo_log import versionutils
import six

from keystone.common import clean
from keystone.common import driver_hints
from keystone.common import models
from keystone import exception
from keystone.i18n import _
from keystone import identity

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Identity(identity.IdentityDriverV8):
    def __init__(self, conf=None):
        super(Identity, self).__init__()
        if conf is None:
            self.conf = CONF
        else:
            self.conf = conf

        # FIXME(knikolla): For rapid prototyping
        self.conf.ldap = cfg.OptGroup('ldap')
        self.conf.ldap.url = 'ipa.demo1.freeipa.org'
        self.conf.ldap.user_name_attribute = 'uid'
        self.conf.ldap.user_id_attribute = 'uid'
        self.conf.ldap.user_tree_dn = 'cn=users, cn=accounts, dc=demo1, dc=freeipa, dc=org'
        self.conf.ldap.group_tree_dn = 'cn=groups, cn=accounts, dc=demo1, dc=freeipa, dc=org'
        self.conf.ldap.user = 'admin'
        self.conf.ldap.password = 'Secret123'

        # Note(knikolla): definition for user object from ldap
        self.user_def = ldap3.ObjectDef('person')
        self.user_def += ldap3.AttrDef(
            self.conf.ldap.user_id_attribute, key='id')
        self.user_def += ldap3.AttrDef(
            self.conf.ldap.user_name_attribute, key='name')

        # Note(knikolla): definition for group object from ldap
        self.group_def = ldap3.ObjectDef('groupOfNames')
        self.group_def += ldap3.AttrDef('cn', key='id')
        self.group_def += ldap3.AttrDef('member', key='members',
                                        dereference_dn=self.user_def)

    def is_domain_aware(self):
        return False

    def generates_uuids(self):
        return False

    def authenticate(self, user_id, password):
        if user_id and password:
            try:
                self._connect(user_id, password)
                return self.get_user(user_id)
            except ldap3.LDAPBindError:
                raise AssertionError(_('Invalid user / password'))
        else:
            raise AssertionError(_('Invalid user / password'))

    def get_user(self, user_id):
        user = ldap3.Reader(
            self._connect(),
            self.user_def,
            '(%s=%s)' % (self.conf.ldap.user_id_attribute, user_id),
            self.conf.ldap.user_tree_dn
        ).search()
        if user:
            return self._construct_user_ref(user[0])
        else:
            raise exception.UserNotFound(user_id=user_id)

    def get_user_by_name(self, user_name, domain_id):
        user = ldap3.Reader(
            self._connect(),
            self.user_def,
            '(%s=%s)' % (self.conf.ldap.user_name_attribute, user_name),
            self.conf.ldap.user_tree_dn
        ).search()
        if user:
            return self._construct_user_ref(user[0])
        else:
            raise exception.UserNotFound(user_id=user_name)

    def list_groups_for_user(self, user_id, hints=None):
        r = ldap3.Reader(
            self._connect(self.conf.ldap.user, self.conf.ldap.password),
            self.group_def,
            '(member=%s)' % self._construct_user_tree_dn(user_id),
            self.conf.ldap.group_tree_dn
        )
        return [x.id.value for x in r.search()]

    def list_users(self, hints=None):
        r = ldap3.Reader(
            self._connect(),
            self.user_def,
            '',
            self.conf.ldap.user_tree_dn
        )
        return [self._construct_user_ref(x) for x in r.search()]

    def check_user_in_group(self, user_id, group_id):
        # Note(knikolla): The interface expects us to raise exceptions if
        # the user or group are not found.
        self.get_user(user_id)
        self.get_group(group_id)

        r = ldap3.Reader(
            self._connect(self.conf.ldap.user, self.conf.ldap.password),
            self.group_def,
            '(member=%s)' % self._construct_user_tree_dn(user_id),
            'cn=%s, %s' % (group_id, self.conf.ldap.group_tree_dn)
        ).search()
        return len(r) > 0

    def list_users_in_group(self, group_id, hints=None):
        group = ldap3.Reader(
            self._connect(self.conf.ldap.user, self.conf.ldap.password),
            self.group_def,
            '',
            'cn=%s, %s' % (group_id, self.conf.ldap.group_tree_dn)
        ).search()
        if group:
            return [self._construct_user_ref(x) for x in group[0].members]
        else:
            return []

    def get_group(self, group_id):
        group = ldap3.Reader(
            self._connect(),
            self.group_def,
            '',
            'cn=%s, %s' % (group_id, self.conf.ldap.group_tree_dn)
        ).search()[0]
        if group:
            return dict() # FIXME(knikolla): Not sure what's in group_ref
        else:
            raise exception.GroupNotFound(group_id=group_id)

    def get_group_by_name(self, group_name, domain_id):
        return self.get_group(group_name)

    def list_groups(self, hints=None):
        r = ldap3.Reader(
            self._connect(self.conf.ldap.user, self.conf.ldap.password),
            self.group_def,
            '',
            self.conf.ldap.group_tree_dn
        )
        return [x.id.value for x in r.search()]

    def _connect(self, user_id=None, password=None):
        if user_id and password:
            user = self._construct_user_tree_dn(user_id)
        else:
            user = None

        conn = ldap3.Connection(
            self.conf.ldap.url,
            auto_bind=True,
            user=user,
            password=password,
            check_names=True,
            read_only=True
        )
        return conn

    def _construct_user_tree_dn(self, user_id):
        return '%s=%s, %s' % (
            self.conf.ldap.user_id_attribute,
            user_id,
            self.conf.ldap.user_tree_dn)

    def _construct_user_ref(self, user):
        user_ref = dict()
        user_ref['name'] = user['name'].value
        user_ref['id'] = user['id'].value
        user_ref['domain_id'] = 'Default' # FIXME(knikolla)
        user_ref['default_project_id'] = None # FIXME(knikolla)
        user_ref['enabled'] = True # FIXME(knikolla)
        return identity.filter_user(user_ref)

    # Note(knikolla): Driver is read only so methods below are not supported.
    def create_user(self, user_id, user):
        raise exception.Forbidden(_("ldap does not support write operations"))

    def update_user(self, user_id, user):
        raise exception.Forbidden(_("ldap does not support write operations"))

    def delete_user(self, user_id):
        raise exception.Forbidden(_("ldap does not support write operations"))

    def add_user_to_group(self, user_id, group_id):
        raise exception.Forbidden(_("ldap does not support write operations"))

    def remove_user_from_group(self, user_id, group_id):
        raise exception.Forbidden(_("ldap does not support write operations"))

    def create_group(self, group_id, group):
        raise exception.Forbidden(_("ldap does not support write operations"))

    def update_group(self, group_id, group):
        raise exception.Forbidden(_("ldap does not support write operations"))

    def delete_group(self, group_id):
        raise exception.Forbidden(_("ldap does not support write operations"))
