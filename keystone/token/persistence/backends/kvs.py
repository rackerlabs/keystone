# Copyright 2013 Metacloud, Inc.
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
import copy
import threading

from oslo_log import log
from oslo_utils import timeutils
import six

from keystone.common import kvs
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone.i18n import _, _LE, _LW
from keystone import token
from keystone.token import provider


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)

STORE_CONF_LOCK = threading.Lock()


class Token(token.persistence.TokenDriverV8):
    """KeyValueStore backend for tokens.

    This is the base implementation for any/all key-value-stores (e.g.
    memcached) for the Token backend.  It is recommended to only use the base
    in-memory implementation for testing purposes.
    """

    revocation_key = 'revocation-list'
    kvs_backend = 'openstack.kvs.Memory'

    def __init__(self, backing_store=None, **kwargs):
        super(Token, self).__init__()
        self._store = kvs.get_key_value_store('token-driver')
        if backing_store is not None:
            self.kvs_backend = backing_store
        # Using a lock here to avoid race condition.
        with STORE_CONF_LOCK:
            if not self._store.is_configured:
                # Do not re-configure the backend if the store has been
                # initialized.
                self._store.configure(backing_store=self.kvs_backend, **kwargs)
        if self.__class__ == Token:
            # NOTE(morganfainberg): Only warn if the base KVS implementation
            # is instantiated.
            LOG.warning(_LW('It is recommended to only use the base '
                            'key-value-store implementation for the token '
                            'driver for testing purposes. Please use '
                            "'memcache' or 'sql' instead."))

    def _prefix_token_id(self, token_id):
        if six.PY2:
            token_id = token_id.encode('utf-8')
        return 'token-%s' % token_id

    def _prefix_user_id(self, user_id):
        if six.PY2:
            user_id = user_id.encode('utf-8')
        return 'usertokens-%s' % user_id

    def _get_key_or_default(self, key, default=None):
        try:
            return self._store.get(key)
        except exception.NotFound:
            return default

    def _get_key(self, key):
        return self._store.get(key)

    def _set_key(self, key, value, lock=None):
        self._store.set(key, value, lock)

    def _delete_key(self, key):
        return self._store.delete(key)

    def get_token(self, token_id):
        ptk = self._prefix_token_id(token_id)
        try:
            token_ref = self._get_key(ptk)
        except exception.NotFound:
            raise exception.TokenNotFound(token_id=token_id)

        return token_ref

    def create_token(self, token_id, data):
        """Create a token by id and data.

        It is assumed the caller has performed data validation on the "data"
        parameter.
        """
        data_copy = copy.deepcopy(data)
        ptk = self._prefix_token_id(token_id)
        if not data_copy.get('expires'):
            data_copy['expires'] = provider.default_expire_time()
        if not data_copy.get('user_id'):
            data_copy['user_id'] = data_copy['user']['id']

        # NOTE(morganfainberg): for ease of manipulating the data without
        # concern about the backend, always store the value(s) in the
        # index as the isotime (string) version so this is where the string is
        # built.
        expires_str = utils.isotime(data_copy['expires'], subsecond=True)

        self._set_key(ptk, data_copy)
        user_id = data['user']['id']
        user_key = self._prefix_user_id(user_id)
        self._update_user_token_list(user_key, token_id, expires_str)
        if CONF.trust.enabled and data.get('trust_id'):
            # NOTE(morganfainberg): If trusts are enabled and this is a trust
            # scoped token, we add the token to the trustee list as well.  This
            # allows password changes of the trustee to also expire the token.
            # There is no harm in placing the token in multiple lists, as
            # _list_tokens is smart enough to handle almost any case of
            # valid/invalid/expired for a given token.
            token_data = data_copy['token_data']
            if data_copy['token_version'] == token.provider.V2:
                trustee_user_id = token_data['access']['trust'][
                    'trustee_user_id']
            elif data_copy['token_version'] == token.provider.V3:
                trustee_user_id = token_data['OS-TRUST:trust'][
                    'trustee_user_id']
            else:
                raise exception.UnsupportedTokenVersionException(
                    _('Unknown token version %s') %
                    data_copy.get('token_version'))

            trustee_key = self._prefix_user_id(trustee_user_id)
            self._update_user_token_list(trustee_key, token_id, expires_str)

        return data_copy

    def _get_user_token_list_with_expiry(self, user_key):
        """Return user token list with token expiry.

        :return: the tuples in the format (token_id, token_expiry)
        :rtype: list
        """
        return self._get_key_or_default(user_key, default=[])

    def _get_user_token_list(self, user_key):
        """Return a list of token_ids for the user_key."""
        token_list = self._get_user_token_list_with_expiry(user_key)
        # Each element is a tuple of (token_id, token_expiry). Most code does
        # not care about the expiry, it is stripped out and only a
        # list of token_ids are returned.
        return [t[0] for t in token_list]

    def _bisect(self, token_list, tstamp, before=True):
        """Locate the insertion point for the token in token_list.

        This function implements a bisection algorithm which finds the index
        of insertion for a value with the specified timestamp. The value
        returned by this function is suitable for use in the list.insert()
        method. The before parameter determines whether the bisection
        algorithm is a bisect_left (before = True) or a bisect_right (before
        = False) algorithm.

        :param token_list: the list of token tuples in the form of
                           (token_id, token_expiry)
        :param tstamp: the token expiry time to determine where the insertion
                       should happen
        :param before: when True finds the insertion point before the specified
                       timestamp value. When False, finds the insertion point
                       after the specified timestamp value.
        :return: index where to insert the token
        """
        low = 0
        high = len(token_list)
        expires = tstamp
        if isinstance(expires, six.string_types):
            expires = timeutils.normalize_time(
                timeutils.parse_isotime(expires))

        while low < high:
            mid = (low + high) // 2
            c_expires = self._get_expire_at(token_list[mid])
            if before:
                if c_expires < expires:
                    low = mid + 1
                else:
                    high = mid
            else:
                if expires < c_expires:
                    high = mid
                else:
                    low = mid + 1
        return low

    def _get_expire_at(self, token):
        """Return the time the token will expire at.

        :param token: the token to check the expiration timestamp of. Formats
                      include (token_id, token_expiration) tuple and a dict
                      with an 'expires' key.
        :return: the normalized form of the expiration time.
        """
        if isinstance(token, tuple):
            _, expire_at = self._format_token_index_item(token)
        elif 'expires' in token:
            expire_at = timeutils.normalize_time(
                timeutils.parse_isotime(token['expires']))
        else:
            # This would be an error in which the wrong data types are
            # passed to this function. It expects only to have either a
            # list of tuples or a list of dicts. Anything else which
            # doesn't satisfy this criteria is a programming error.
            raise ValueError('Expected (token_id, token_expiration) tuple or '
                             'a dict with the "expires" key.')
        return expire_at

    def _update_user_token_list(self, user_key, token_id, expires_isotime_str):
        current_time = self._get_current_time()
        revoked_token_list = set([t['id'] for t in
                                  self.list_revoked_tokens()])

        with self._store.get_lock(user_key) as lock:
            filtered_list = []
            token_list = self._get_user_token_list_with_expiry(user_key)
            expired_index = self._bisect(token_list, current_time, before=True)

            # Since the list is maintained in sorted order according to the
            # expiration timestamp with the earliest expiration at the head
            # of the list and the latest expiration at the tail, the list
            # should be trimmed to include only those beyond the expired_index.
            # Any tokens not included in the token list are expired and should
            # be removed.
            token_list = token_list[expired_index:]
            revoked_tokens = []

            for item in token_list:
                item_id = item[0]

                if item_id in revoked_token_list:
                    # NOTE(morganfainberg): If the token has been revoked, it
                    # can safely be removed from this list.  This helps to keep
                    # the user_token_list as reasonably small as possible.
                    revoked_tokens.append(item_id)
                    continue

                # These should already be in sorted order, therefore an append
                # will be simple enough to maintain order.
                filtered_list.append(item)

            # If tokens were excluded because they were revoked, include a
            # debug message in the log. Logging each entry is inefficient for
            # large loops.
            if revoked_tokens:
                LOG.debug(('Tokens `%(token_ids)s` are revoked, removing '
                           'from `%(user_key)s`.'),
                          {'token_ids': ', '.join(revoked_tokens),
                           'user_key': user_key})

            # Insert the new item where it should be in sorted order based
            # upon the key expiration.
            idx = self._bisect(token_list, expires_isotime_str, before=False)
            filtered_list.insert(idx, (token_id, expires_isotime_str))
            self._set_key(user_key, filtered_list, lock)
            return filtered_list

    def _get_current_time(self):
        return timeutils.normalize_time(timeutils.utcnow())

    def _add_to_revocation_list(self, data, lock):
        filtered_list = []
        revoked_token_data = {}

        current_time = self._get_current_time()
        expires = data['expires']

        if isinstance(expires, six.string_types):
            expires = timeutils.parse_isotime(expires)

        expires = timeutils.normalize_time(expires)

        if expires < current_time:
            LOG.warning(_LW('Token `%s` is expired, not adding to the '
                            'revocation list.'), data['id'])
            return

        revoked_token_data['expires'] = utils.isotime(expires,
                                                      subsecond=True)
        revoked_token_data['id'] = data['id']

        token_data = data['token_data']
        if 'access' in token_data:
            # It's a v2 token.
            audit_ids = token_data['access']['token']['audit_ids']
        else:
            # It's a v3 token.
            audit_ids = token_data['token']['audit_ids']
        revoked_token_data['audit_id'] = audit_ids[0]

        token_list = self._get_key_or_default(self.revocation_key, default=[])
        if not isinstance(token_list, list):
            # NOTE(morganfainberg): In the case that the revocation list is not
            # in a format we understand, reinitialize it. This is an attempt to
            # not allow the revocation list to be completely broken if
            # somehow the key is changed outside of keystone (e.g. memcache
            # that is shared by multiple applications). Logging occurs at error
            # level so that the cloud administrators have some awareness that
            # the revocation_list needed to be cleared out. In all, this should
            # be recoverable. Keystone cannot control external applications
            # from changing a key in some backends, however, it is possible to
            # gracefully handle and notify of this event.
            LOG.error(_LE('Reinitializing revocation list due to error '
                          'in loading revocation list from backend.  '
                          'Expected `list` type got `%(type)s`. Old '
                          'revocation list data: %(list)r'),
                      {'type': type(token_list), 'list': token_list})
            token_list = []

        # NOTE(morganfainberg): on revocation, cleanup the expired entries, try
        # to keep the list of tokens revoked at the minimum.
        expired_index = self._bisect(token_list, current_time, before=True)
        filtered_list = token_list[expired_index:]

        # Insert the revoked token at the appropriate place in the list to
        # maintain the sorted order of the revocation list.
        insertion_index = self._bisect(token_list, expires, before=False)
        filtered_list.insert(insertion_index, revoked_token_data)

        self._set_key(self.revocation_key, filtered_list, lock)

    def delete_token(self, token_id):
        # Test for existence
        with self._store.get_lock(self.revocation_key) as lock:
            data = self.get_token(token_id)
            ptk = self._prefix_token_id(token_id)
            result = self._delete_key(ptk)
            self._add_to_revocation_list(data, lock)
        return result

    def delete_tokens(self, user_id, tenant_id=None, trust_id=None,
                      consumer_id=None):
        return super(Token, self).delete_tokens(
            user_id=user_id,
            tenant_id=tenant_id,
            trust_id=trust_id,
            consumer_id=consumer_id,
        )

    def _format_token_index_item(self, item):
        try:
            token_id, expires = item
        except (TypeError, ValueError):
            LOG.debug(('Invalid token entry expected tuple of '
                       '`(<token_id>, <expires>)` got: `%(item)r`'),
                      dict(item=item))
            raise

        try:
            expires = timeutils.normalize_time(
                timeutils.parse_isotime(expires))
        except ValueError:
            LOG.debug(('Invalid expires time on token `%(token_id)s`:'
                       ' %(expires)r'),
                      dict(token_id=token_id, expires=expires))
            raise
        return token_id, expires

    def _token_match_tenant(self, token_ref, tenant_id):
        if token_ref.get('tenant'):
            return token_ref['tenant'].get('id') == tenant_id
        return False

    def _token_match_trust(self, token_ref, trust_id):
        if not token_ref.get('trust_id'):
            return False
        return token_ref['trust_id'] == trust_id

    def _token_match_consumer(self, token_ref, consumer_id):
        try:
            oauth = token_ref['token_data']['token']['OS-OAUTH1']
            return oauth.get('consumer_id') == consumer_id
        except KeyError:
            return False

    def _list_tokens(self, user_id, tenant_id=None, trust_id=None,
                     consumer_id=None):
        # This function is used to generate the list of tokens that should be
        # revoked when revoking by token identifiers.  This approach will be
        # deprecated soon, probably in the Juno release.  Setting revoke_by_id
        # to False indicates that this kind of recording should not be
        # performed.  In order to test the revocation events, tokens shouldn't
        # be deleted from the backends.  This check ensures that tokens are
        # still recorded.
        if not CONF.token.revoke_by_id:
            return []
        tokens = []
        user_key = self._prefix_user_id(user_id)
        token_list = self._get_user_token_list_with_expiry(user_key)
        current_time = self._get_current_time()

        # The token_list returned from _get_user_token_list_with_expiry is a
        # list of (token_id, expiration_tstamp) tuples. Use the bisect call
        # to find the index in the list which is where the current timestamp
        # would be inserted. All items in the list less than the point where
        # the current time would be inserted can be considered expired, and
        # can be removed from the list.
        expired_index = self._bisect(token_list, current_time, before=True)
        token_list = token_list[expired_index:]

        for item in token_list:
            # Each item in the token_list is a (token_id, expiration_tstamp)
            # tuple but only the token_id is needed here.
            token_id = item[0]

            try:
                token_ref = self.get_token(token_id)
            except exception.TokenNotFound:  # nosec(tkelsey)
                # NOTE(morganfainberg): Token doesn't exist, skip it.
                continue
            if token_ref:
                if tenant_id is not None:
                    if not self._token_match_tenant(token_ref, tenant_id):
                        continue
                if trust_id is not None:
                    if not self._token_match_trust(token_ref, trust_id):
                        continue
                if consumer_id is not None:
                    if not self._token_match_consumer(token_ref, consumer_id):
                        continue

                tokens.append(token_id)
        return tokens

    def list_revoked_tokens(self):
        revoked_token_list = self._get_key_or_default(self.revocation_key,
                                                      default=[])
        if isinstance(revoked_token_list, list):
            return revoked_token_list
        return []

    def flush_expired_tokens(self):
        """Archive or delete tokens that have expired."""
        raise exception.NotImplemented()
