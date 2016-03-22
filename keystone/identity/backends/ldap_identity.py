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

import ldap3
from oslo_config import cfg
from oslo_log import log

from keystone.common import driver_hints
from keystone import exception
from keystone.i18n import _
from keystone import identity

CONF = cfg.CONF
LOG = log.getLogger(__name__)

READ_ONLY_LDAP_ERROR_MESSAGE = _("LDAP does not support write operations")


class Identity(identity.IdentityDriverV8):
    # TODO(knikolla): WIP
    # user enabled mask
    # auth connection pool
    # more attributes
    def __init__(self, conf=None):
        super(Identity, self).__init__()
        self.conf = self._get_conf()

        # FIXME(knikolla): For rapid prototyping
        self.conf.insecure_debug = False
        self.conf.ldap = cfg.OptGroup('ldap')

        self.conf.ldap.url = 'ipa.demo1.freeipa.org'
        self.conf.ldap.user = 'uid=admin'
        self.conf.ldap.password = 'Secret123'
        self.conf.ldap.user_tree_dn = 'cn=users, cn=accounts, dc=demo1, ' \
                                      'dc=freeipa, dc=org'
        self.conf.ldap.group_tree_dn = 'cn=groups, cn=accounts, dc=demo1, ' \
                                       'dc=freeipa, dc=org'

        self.conf.ldap.domain_id = 'Default'
        self.conf.ldap.query_scope = 'sub'

        # Pooling
        self.conf.ldap.use_pool = True
        self.conf.ldap.pool_size = 5
        self.conf.ldap.pool_connection_lifetime = 600
        self.conf.ldap.use_auth_pool = True
        self.conf.ldap.auth_pool_size = 100
        self.conf.ldap.auth_pool_connection_lifetime = 60

        self.conf.ldap.user_objectclass = 'person'
        self.conf.ldap.user_name_attribute = 'uid'
        self.conf.ldap.user_id_attribute = 'uid'
        self.conf.ldap.user_description_attribute = 'uid'
        self.conf.ldap.user_enabled_attribute = 'nsAccountLock'
        self.conf.ldap.user_enabled_invert = True

        self.conf.ldap.group_objectclass = 'groupOfNames'
        self.conf.ldap.group_id_attribute = 'cn'
        self.conf.ldap.group_name_attribute = 'cn'
        self.conf.ldap.group_description_attribute = 'cn'
        self.conf.ldap.group_member_attribute = 'member'
        # End of config options

        self.read_only = True

        # Note(knikolla): definition for user object from ldap
        self.user_def = ldap3.ObjectDef(self.conf.ldap.user_objectclass)
        self.user_def += 'cn'
        self.user_def += ldap3.AttrDef(
            name=self.conf.ldap.user_id_attribute,
            key='id'
        )
        self.user_def += ldap3.AttrDef(
            name=self.conf.ldap.user_name_attribute,
            key='name'
        )
        self.user_def += ldap3.AttrDef(
            name=self.conf.ldap.user_description_attribute,
            key='description'
        )
        self.user_def += ldap3.AttrDef(
            name=self.conf.ldap.user_enabled_attribute,
            key='enabled'
        )

        # Note(knikolla): definition for group object from ldap
        self.group_def = ldap3.ObjectDef(self.conf.ldap.group_objectclass)
        self.group_def += ldap3.AttrDef(
            name=self.conf.ldap.group_id_attribute,
            key='id'
        )
        self.group_def += ldap3.AttrDef(
            name=self.conf.ldap.group_name_attribute,
            key='name'
        )
        self.group_def += ldap3.AttrDef(
            name=self.conf.ldap.group_description_attribute,
            key='description'
        )
        self.group_def += ldap3.AttrDef(
            name=self.conf.ldap.group_member_attribute,
            key='members',
            dereference_dn=self.user_def
        )

        if self.conf.ldap.user_tree_dn is None:
            self.conf.ldap.user_tree_dn = self.conf.ldap.suffix

        if self.conf.ldap.group_tree_dn is None:
            self.conf.ldap.group_tree_dn = self.conf.ldap.suffix

    def is_domain_aware(self):
        return False

    def generates_uuids(self):
        return False

    def authenticate(self, user_id, password):
        if user_id and password:
            try:
                conn = self._connect(user_id, password, is_auth=True)
                conn.bind()
                conn.unbind()
                return self.get_user(user_id)
            except ldap3.LDAPBindError:
                raise AssertionError(_('Invalid user / password'))
        else:
            raise AssertionError(_('Invalid user / password'))

    def get_user(self, user_id):
        query = self._construct_query(
            attribute=self.conf.ldap.user_id_attribute,
            value=user_id
        )
        users = self._search_users(query)
        if users:
            return self._construct_user_ref(users[0])
        else:
            raise exception.UserNotFound(user_id=user_id)

    def get_user_by_name(self, user_name, domain_id):
        query = self._construct_query(
            attribute=self.conf.ldap.user_name_attribute,
            value=user_name
        )
        users = self._search_users(query)
        if users:
            return self._construct_user_ref(users[0])
        else:
            raise exception.UserNotFound(user_id=user_name)

    def list_groups_for_user(self, user_id, hints=None):
        query = self._construct_query(
            attribute=self.conf.ldap.group_member_attribute,
            value=self._construct_user_tree_dn(user_id)
        )
        groups = self._search_groups(query, hints=hints)
        return [self._construct_group_ref(x) for x in groups]

    def list_users(self, hints=None):
        users = self._search_users(hints=hints)
        return [self._construct_user_ref(x) for x in users]

    def check_user_in_group(self, user_id, group_id):
        # Note(knikolla): The interface expects us to raise exceptions if
        # the user or group are not found.
        self.get_user(user_id)
        self.get_group(group_id)

        query = self._construct_query(
            attribute=self.conf.ldap.group_member_attribute,
            value=self._construct_user_tree_dn(user_id)
        )
        base = self._construct_group_tree_dn(group_id)
        result = self._search_groups(query, base)
        return len(result) > 0

    def list_users_in_group(self, group_id, hints=None):
        base = self._construct_group_tree_dn(group_id)
        groups = self._search_groups(base=base, hints=hints)

        if groups:
            return [self._construct_user_ref(x) for x in groups[0].members]
        else:
            return []

    def get_group(self, group_id):
        base = self._construct_group_tree_dn(group_id)
        groups = self._search_groups(base=base)
        if groups:
            return self._construct_group_ref(groups[0])
        else:
            raise exception.GroupNotFound(group_id=group_id)

    def get_group_by_name(self, group_name, domain_id):
        query = self._construct_query(
            attribute=self.conf.ldap.group_name_attribute,
            value=group_name
        )
        groups = self._search_groups(query)
        if groups:
            return self._construct_group_ref(groups[0])
        else:
            raise exception.GroupNotFound(group_id=group_name)

    def list_groups(self, hints=None):
        groups = self._search_groups(hints=hints)
        return [self._construct_group_ref(x) for x in groups]

    def _connect(self, user_id=None, password=None, is_auth=False):
        if user_id and password:
            user = self._construct_user_tree_dn(user_id)
        else:
            user = None

        use_pool = False
        if self.conf.ldap.use_pool:
            if is_auth and self.conf.ldap.use_auth_pool:
                # FIXME(knikolla): Doesn't work ATM, always authenticates even
                # with wrong password.
                use_pool = False  # FIXME(knikolla): True once issue resolved
                pool_name = 'auth_pool'
                pool_size = self.conf.ldap.auth_pool_size
                pool_lifetime = self.conf.ldap.auth_pool_connection_lifetime
            elif not is_auth:
                use_pool = True
                pool_name = 'search_pool'
                pool_size = self.conf.ldap.pool_size
                pool_lifetime = self.conf.ldap.pool_connection_lifetime

        conn = ldap3.Connection(
            self.conf.ldap.url,
            auto_bind=True,
            user=user if is_auth else '%s,%s' % (
                self.conf.ldap.user, self.conf.ldap.user_tree_dn),
            password=password if is_auth else self.conf.ldap.password,
            check_names=True,
            read_only=self.read_only,
            client_strategy=ldap3.SYNC if not use_pool else ldap3.REUSABLE,
            raise_exceptions=True,
            pool_name=None if not use_pool else pool_name,
            pool_size=None if not use_pool else pool_size,
            pool_lifetime=None if not use_pool else pool_lifetime
        )
        return conn

    def _construct_user_tree_dn(self, user_id):
        return '%s=%s, %s' % (
            self.conf.ldap.user_id_attribute,
            user_id,
            self.conf.ldap.user_tree_dn)

    def _construct_group_tree_dn(self, group_id):
        return '%s=%s, %s' % (
            self.conf.ldap.group_id_attribute,
            group_id,
            self.conf.ldap.group_tree_dn)

    def _construct_query(self, attribute, value):
        return '(%(attr_name)s=%(attr_value)s)' % {
            'attr_name': attribute,
            'attr_value': value
        }

    def _construct_user_ref(self, user):
        user_ref = dict()
        user_ref['name'] = user['name'].value
        user_ref['id'] = user['id'].value
        user_ref['domain_id'] = self.conf.ldap.domain_id
        user_ref['default_project_id'] = None  # FIXME(knikolla)
        user_ref['enabled'] = self._is_user_enabled(user)
        return identity.filter_user(user_ref)

    def _construct_group_ref(self, group):
        group_ref = dict()
        group_ref['name'] = group['name'].value
        group_ref['id'] = group['id'].value
        group_ref['domain_id'] = self.conf.ldap.domain_id
        group_ref['description'] = group['description'].value
        return group_ref

    @driver_hints.truncated
    def _search(self, hints, object_def, query, base):
        if query is None:
            query = ''

        reader = ldap3.Reader(
            connection=self._connect(is_auth=False),
            object_def=object_def,
            query=query,
            base=base
        )
        # Note(knikolla): Even though the decorator truncates the list
        # we are still fetching all the values.
        # ldap3 reader has a reader method search_size_limit(limit)
        # which is alternative to the two search methods below,
        # so I'm not sure if it preserves the query scope.
        if self.conf.ldap.query_scope == 'one':
            return reader.search()
        elif self.conf.ldap.query_scope == 'sub':
            return reader.search_subtree()
        else:
            raise AssertionError(_('Invalid query scope'))

    def _search_users(self, query=None, base=None, hints=None):
        if base is None:
            base = self.conf.ldap.user_tree_dn
        if hints is None:
            hints = driver_hints.Hints()

        return self._search(hints, self.user_def, query, base)

    def _search_groups(self, query=None, base=None, hints=None):
        if base is None:
            base = self.conf.ldap.group_tree_dn
        if hints is None:
            hints = driver_hints.Hints()

        return self._search(hints, self.group_def, query, base)

    def _is_user_enabled(self, user):
        if hasattr(user, 'enabled'):
            enabled = True if user.enabled.value.lower() == 'true' else False
            if self.conf.ldap.user_enabled_invert:
                enabled = not enabled
        else:
            enabled = False
        return enabled

    # Note(knikolla): Driver is read only so methods below are not supported.
    def create_user(self, user_id, user):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)

    def update_user(self, user_id, user):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)

    def delete_user(self, user_id):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)

    def add_user_to_group(self, user_id, group_id):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)

    def remove_user_from_group(self, user_id, group_id):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)

    def create_group(self, group_id, group):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)

    def update_group(self, group_id, group):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)

    def delete_group(self, group_id):
        raise exception.Forbidden(READ_ONLY_LDAP_ERROR_MESSAGE)


class IdentityRW(Identity):
    """For unit tests that require creating users."""

    def __init__(self, conf=None):
        super(IdentityRW, self).__init__(conf)
        self.read_only = False
        self.conf.ldap.use_pool = False

    def create_user(self, user_id, user):
        # FIXME(knikolla): Doesn't work with FreeIPA when id attr is uid
        conn = self._connect()
        conn.add(
            self._construct_user_tree_dn(user_id),
            self.conf.ldap.user_objectclass,
            {
                # FIXME(knikolla): Update to include all attributes
                'sn': user_id,
                self.conf.ldap.user_name_attribute: user['name'],
                self.conf.ldap.user_description_attribute: user['description']
            }
        )

    def update_user(self, user_id, user):
        conn = self._connect()
        conn.modify(
            self._construct_user_tree_dn(user_id),
            {
                # FIXME(knikolla): Update to include all attributes
                self.conf.ldap.user_description_attribute: user['description']
            }
        )

    def delete_user(self, user_id):
        conn = self._connect()
        conn.delete(self._construct_user_tree_dn(user_id))

    def add_user_to_group(self, user_id, group_id):
        self.get_user(user_id)

        conn = self._connect()
        conn.modify(
            self._construct_group_tree_dn(group_id),
            {
                self.conf.ldap.group_member_attribute: [
                    ldap3.MODIFY_ADD,
                    self._construct_user_tree_dn(user_id)
                ]
            }
        )

    def remove_user_from_group(self, user_id, group_id):
        self.get_user(user_id)

        conn = self._connect()
        conn.modify(
            self._construct_group_tree_dn(group_id),
            {
                self.conf.ldap.group_member_attribute: [
                    ldap3.MODIFY_DELETE,
                    self._construct_user_tree_dn(user_id)
                ]
            }
        )

    def create_group(self, group_id, group):
        conn = self._connect()
        conn.add(
            self._construct_group_tree_dn(group_id),
            self.conf.ldap.group_objectclass
        )

    def update_group(self, group_id, group):
        conn = self._connect()
        conn.modify(
            self._construct_group_tree_dn(group_id),
            {
                # FIXME(knikolla): Update to include all attributes
                self.conf.ldap.group_description_attribute: [
                    ldap3.MODIFY_REPLACE,
                    group['description']
                ]
            }
        )

    def delete_group(self, group_id):
        conn = self._connect()
        conn.delete(self._construct_group_tree_dn(group_id))
