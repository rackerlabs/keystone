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
                    with os.open(opt[len('file://'):], flags, 0600) as f:
                        self.mkey = self.crypto.new_key(KEY_SIZE)
                        os.write(f, base64.b64encode(self.mkey))
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

    def _get_key(self, key_id):
        """Decrypts the provided encoded key and returns
        the clear text key.

        :param key_id: Key Identifier
        """
        # Get Requestor's encypted key
        key = self.driver.get_shared_key(key_id)
        if not key:
            raise exception.Unauthorized('Invalid Requestor')

        return self._decrypt_keyblock(key_id, key)

    def _set_key(self, key_id, keyblock):
        """Encrypts the provided key and stores it.

        :param keyblock: The key to encrypt
        """
        sig, enc = self._encrypt_keyblock(key_id, keyblock)
        self.driver.set_shared_key(key_id, sig + enc)

    def get_ticket(self, context, req):
        if not ('metadata' in req):
            raise exception.Forbidden('Invalid Request format')
        try:
            meta = jsonutils.loads(base64.b64decode(req['metadata']))
        except Exception:
            raise exception.Forbidden('Invalid Request format')

        if not ('requestor' in meta):
            raise exception.Forbidden('Invalid Request format')

        rkey = self._get_key(meta['requestor'])

        try:
            signature = self.crypto.sign(rkey, req['metadata'])
        except Exception:
            raise exception.Unauthorized('Invalid Request')

        if signature != req['signature']:
            raise exception.Unauthorized('Invalid Request')

        timestamp = time.time()

        if meta['timestamp'] < (timestamp - self.ttl):
            raise exception.Unauthorized('Invalid Request (expired)')

        #TODO(simo): check and store signature for replay attack detection

        tkey = self._get_key(meta['target'])
        if not tkey:
            raise exception.Unauthorized('Invalid Target')

        # use new_key to get a random salt
        rndkey = self.hkdf.extract(rkey, self.crypto.new_key(KEY_SIZE))

        info = '%s,%s,%s' % (meta['requestor'], meta['target'], str(timestamp))

        sek = self.hkdf.expand(rndkey, info, KEY_SIZE * 2)
        skey, ekey = self._split_key(sek, KEY_SIZE)
        keydata = {'key': base64.b64encode(rndkey),
                   'timestamp': timestamp, 'ttl': self.ttl}
        esek = self.crypto.encrypt(tkey, jsonutils.dumps(keydata))
        ticket = jsonutils.dumps({'skey': base64.b64encode(skey),
                                  'ekey': base64.b64encode(ekey),
                                  'esek': esek})

        rep = dict()
        metadata = jsonutils.dumps({'source': meta['requestor'],
                                    'destination': meta['target'],
                                    'expiration': (keydata['timestamp']
                                                   + keydata['ttl']),
                                    'encryption': True})
        rep['metadata'] = base64.b64encode(metadata)
        rep['ticket'] = self.crypto.encrypt(rkey, ticket)
        rep['signature'] = self.crypto.sign(rkey,
                                            (rep['metadata'] + rep['ticket']))

        return {'reply': rep}

    def set_key(self, context, req):
        self._set_key(req['owner'], base64.b64decode(req['key']))


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
