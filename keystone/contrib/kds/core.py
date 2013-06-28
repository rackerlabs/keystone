# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
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

"""Main entry point into the Key distribution Server service."""

import base64
import errno
import os
import time

from keystone.openstack.common.crypto import utils as cryptoutils
from keystone.openstack.common import jsonutils

from keystone.common import dependency
from keystone.common import logging
from keystone.common import manager
from keystone import config
from keystone import exception


CONF = config.CONF
LOG = logging.getLogger(__name__)
KEY_SIZE = 16
GROUP_KEY_TTL = 900  # 15 minutes


@dependency.provider('kds_api')
class Manager(manager.Manager):
    """Default pivot point for the KDS backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        self.crypto = cryptoutils.SymmetricCrypto(enctype=CONF.kds.enctype,
                                                  hashtype=CONF.kds.hashtype)
        self.hkdf = cryptoutils.HKDF(hashtype=CONF.kds.hashtype)
        self.ttl = int(CONF.kds.ticket_lifetime)
        opt = CONF.kds.master_key.strip()
        if opt.startswith('file:'):
            try:
                with open(opt[len('file://'):], 'r') as f:
                    self.mkey = base64.b64decode(f.read())
            except IOError as e:
                if e.errno == errno.ENOENT:
                    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                    try:
                        f = os.open(opt[len('file://'):], flags, 0600)
                        self.mkey = self.crypto.new_key(KEY_SIZE)
                        os.write(f, base64.b64encode(self.mkey))
                    except Exception:
                        os.remove(opt[len('file://'):])
                    finally:
                        if f > 0:
                            os.close(f)
                else:
                    raise
        else:
            raise Exception('Invalid Master Key Option')

        if len(self.mkey) != KEY_SIZE:
            raise Exception('Invalid Master Key Size')

        super(Manager, self).__init__(CONF.kds.driver)

    def _split_key(self, key, size):
        sig_key = key[:size]
        enc_key = key[size:]
        return sig_key, enc_key

    def _get_master_keys(self, key_id):
        if not self.mkey:
            raise exception.UnexpectedError('Failed to find mkey')

        km = self.hkdf.expand(self.mkey, key_id, 2 * KEY_SIZE)
        return self._split_key(km, KEY_SIZE)

    def _encrypt_keyblock(self, key_id, keyblock):
        skey, ekey = self._get_master_keys(key_id)
        try:
            enc = self.crypto.encrypt(ekey, keyblock, b64encode=False)
        except Exception:
            raise exception.UnexpectedError('Failed to encrypt key')

        try:
            sig = self.crypto.sign(skey, enc, b64encode=False)
        except Exception:
            raise exception.UnexpectedError('Failed to sign key')

        return sig, enc

    def _decrypt_keyblock(self, key_id, keyblock):
        sig, enc = self._split_key(keyblock, self.crypto.hashfn.digest_size)
        skey, ekey = self._get_master_keys(key_id)

        # signature check
        try:
            sigc = self.crypto.sign(skey, enc, b64encode=False)
            if not sigc == sig:
                raise exception.UnexpectedError('Signature check failed')
        except Exception:
            raise exception.UnexpectedError('Failed to verify key')

        try:
            plain = self.crypto.decrypt(ekey, enc, b64decode=False)
        except Exception:
            raise exception.UnexpectedError('Failed to decrypt key')

        return plain

    def _gen_group_key(self, key_id):
        """Generates a new group key."""
        exp = time.time() + GROUP_KEY_TTL

        keyblock = self.crypto.new_key(KEY_SIZE)
        sig, enc = self._encrypt_keyblock(keyblock)

        gen = self.driver.set_group_key(key_id, exp, sig + enc)

        return keyblock, gen

    def _get_key(self, key_id, gen=0):
        """Decrypts the provided encoded key and returns
        the clear text key.

        :param key_id: Key Identifier
        """
        # Get Requestor's encypted key
        k = self.driver.get_shared_key(key_id)
        if not k:
            raise exception.Forbidden('Invalid Key ID')
        if 'key_v1' in k:
            if gen != 0:
                raise exception.Forbidden('Invalid Key Type')
            key = base64.b64decode(k['key_v1'])
        elif 'group_keys' in k:
            g = k['group_keys']
            # find a specific generation or throw back an error
            if gen != 0:
                key = base64.b64decode(g[gen]['key_v1'])

            # find one not expired and with at least 10 more
            # minutes lifetime, otherwise build a new generation
            else:
                t = time.time()
                last_gen = k['generation']
                if last_gen in g and g[last_gen]['expiration'] > t:
                    key = base64.b64decode(g[last_gen]['key_v1'])
                else:
                    return self._gen_group_key(key_id)
        else:
            raise exception.UnexpectedError('Unknown key format')

        plain = self._decrypt_keyblock(key_id, key)

        return plain, gen

    def _set_key(self, key_id, keyblock):
        """Encrypts the provided key and stores it.

        :param keyblock: The key to encrypt
        """
        sig, enc = self._encrypt_keyblock(key_id, keyblock)
        self.driver.set_shared_key(key_id, sig + enc)

    def _common_request(self, req):
        if 'metadata' not in req:
            raise exception.Forbidden('Invalid Request format')
        try:
            meta = jsonutils.loads(base64.b64decode(req['metadata']))
        except Exception:
            raise exception.Forbidden('Invalid Request format')

        if 'requestor' not in meta:
            raise exception.Forbidden('Invalid Request format')

        # Requests can be made only by non-group identities
        try:
            rkey, gen = self._get_key(meta['requestor'], 0)
        except exception.UnexpectedError:
            raise exception.Unauthorized('Invalid Request')
        if gen != 0:
            raise exception.Unauthorized('Invalid Request')

        try:
            signature = self.crypto.sign(rkey, req['metadata'])
        except Exception:
            raise exception.Unauthorized('Invalid Request')

        if signature != req['signature']:
            raise exception.Unauthorized('Invalid Request')

        #TODO(simo): check and store signature for replay attack detection

        timestamp = time.time()

        if meta['timestamp'] < (timestamp - self.ttl):
            raise exception.Unauthorized('Invalid Request (expired)')

        return meta, rkey, timestamp

    def get_ticket(self, context, req):

        meta, rkey, timestamp = self._common_request(req)

        source = meta['requestor']
        target = meta['target']

        tkey, gen = self._get_key(target)
        if not tkey:
            raise exception.Unauthorized('Invalid Destination')

        if gen != 0:
            target += ':' + str(gen)

        # use new_key to get a random salt
        rndkey = self.hkdf.extract(rkey, self.crypto.new_key(KEY_SIZE))

        info = '%s,%s,%s' % (source, target, str(timestamp))

        sek = self.hkdf.expand(rndkey, info, KEY_SIZE * 2)
        skey, ekey = self._split_key(sek, KEY_SIZE)
        keydata = {'key': base64.b64encode(rndkey),
                   'timestamp': timestamp, 'ttl': self.ttl}
        esek = self.crypto.encrypt(tkey, jsonutils.dumps(keydata))
        ticket = jsonutils.dumps({'skey': base64.b64encode(skey),
                                  'ekey': base64.b64encode(ekey),
                                  'esek': esek})

        rep = dict()
        metadata = jsonutils.dumps({'source': source, 'destination': target,
                                    'expiration': (timestamp + self.ttl)})
        rep['metadata'] = base64.b64encode(metadata)
        rep['ticket'] = self.crypto.encrypt(rkey, ticket)

        payload = rep['metadata'] + rep['ticket']
        rep['signature'] = self.crypto.sign(rkey, payload)

        return {'reply': rep}

    def get_group_key(self, context, req):

        meta, rkey, timestamp = self._common_request(req)

        source = meta['requestor']
        target = meta['target']

        group = source.split('.')[0]

        if ':' not in target:
            raise exception.Unauthorized('Invalid Target')
        grp, generation = target.split(':')

        if group != grp:
            raise exception.Unauthorized('Invalid Target')

        tkey, gen = self._get_key(group, generation)
        if not tkey:
            raise exception.Unauthorized('Invalid Target')

        rep = dict()
        metadata = jsonutils.dumps({'source': source, 'destination': target,
                                    'expiration': (timestamp + self.ttl)})
        rep['metadata'] = base64.b64encode(metadata)
        rep['group_key'] = self.crypto.encrypt(rkey, tkey)

        payload = rep['metadata'] + rep['group_key']
        rep['signature'] = self.crypto.sign(rkey, payload)

        return {'reply': rep}

    def set_key(self, context, req):
        self._set_key(req['owner'], base64.b64decode(req['key']))

    def create_group(self, context, req):
        self.driver.set_group_key(req['group'])


class Driver(object):
    """Interface description for a KDS driver."""

    def set_shared_key(self, kds_id, key):
        """Set key related to kds_id."""
        raise exception.NotImplemented()

    def get_shared_key(self, kds_id):
        """Get key related to kds_id.

        :returns: key
        :raises: keystone.exception.ServiceNotFound
        """
        raise exception.NotImplemented()
