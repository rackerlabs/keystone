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

from __future__ import absolute_import
import uuid

from ldap3 import Connection, LDAPBindError, ALL_ATTRIBUTES
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

    def is_domain_aware(self):
        return False

    def generates_uuids(self):
        return False

    def _connect(self, user_id=None, password=None):
        if user_id and password:
            user = self._construct_user_tree_dn(user_id)
        else:
            user = None

        conn = Connection(
            self.conf.ldap.url,
            auto_bind=True,
            user=user,
            password=password,
            check_names=True,
            read_only=True
        )
        return conn


    def _construct_user_tree_dn(self, user_id):
        return self.conf.ldap.user_id_attribute + '=' + user_id + ', '\
               + self.conf.ldap.user_tree_dn

    def _construct_user_ref(self, user):
        user_ref = dict()
        user_ref['name'] = user[self.conf.ldap.user_name_attribute]
        user_ref['id'] = user[self.conf.ldap.user_id_attribute]
        user_ref['domain_id'] = 'Default' # FIXME(knikolla)
        user_ref['default_project_id'] = None # FIXME(knikolla)
        user_ref['enabled'] = True # FIXME(knikolla)
        return identity.filter_user(user_ref)

    def authenticate(self, user_id, password):
        if user_id and password:
            try:
                self._connect(user_id, password)
                return self.get_user(user_id)
            except LDAPBindError:
                raise AssertionError(_('Invalid user / password'))
        else:
            raise AssertionError(_('Invalid user / password'))

    def get_user(self, user_id):
        query = '(&(objectclass=person)(' +\
                self.conf.ldap.user_id_attribute + ' =' + user_id + ' ))'
        c = self._connect()
        c.search(
            self.conf.ldap.user_tree_dn,
            query,
            attributes=ALL_ATTRIBUTES)
        return self._construct_user_ref(c.entries[0])

    def get_user_by_name(self, user_name, domain_id):
        query = '(&(objectclass=person)(' +\
                self.conf.ldap.user_name_attribute + ' =' + user_name + ' ))'
        c = self._connect()
        c.search(
            self.conf.ldap.user_tree_dn,
            query,
            attributes=ALL_ATTRIBUTES)
        return self._construct_user_ref(c.entries[0])

    def list_groups_for_user(self, user_id, hints):
        # FIXME(knikolla)
        raise NotImplementedError

    def list_users(self, hints):
        # FIXME(knikolla)
        raise NotImplementedError

    def check_user_in_group(self, user_id, group_id):
        # FIXME(knikolla)
        raise NotImplementedError

    def list_users_in_group(self, group_id, hints):
        # FIXME(knikolla)
        raise NotImplementedError

    def get_group(self, group_id):
        # FIXME(knikolla)
        raise NotImplementedError

    def get_group_by_name(self, group_name, domain_id):
        # FIXME(knikolla)
        raise NotImplementedError

    def list_groups(self, hints):
        # FIXME(knikolla)
        raise NotImplementedError

    # Note(knikolla): Driver is read only so methods below are not supported.
    def create_user(self, user_id, user):
        raise NotImplementedError

    def update_user(self, user_id, user):
        raise NotImplementedError

    def delete_user(self, user_id):
        raise NotImplementedError

    def add_user_to_group(self, user_id, group_id):
        raise NotImplementedError

    def remove_user_from_group(self, user_id, group_id):
        raise NotImplementedError

    def create_group(self, group_id, group):
        raise NotImplementedError

    def update_group(self, group_id, group):
        raise NotImplementedError

    def delete_group(self, group_id):
        raise NotImplementedError
