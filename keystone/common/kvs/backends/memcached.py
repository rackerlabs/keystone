# -*- coding: utf-8 -*-

# Copyright 2013 Metacloud, Inc.
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

"""
Keystone Memcached dogpile.cache backend implementation.
"""

import random
import time

from dogpile.cache import api
from dogpile.cache.backends import memcached

from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.openstack.common import log


CONF = config.CONF
LOG = log.getLogger(__name__)
NO_VALUE = api.NO_VALUE


class MemcachedDriverMixin(object):
    # Basic Mixin for properly handling setting a TTL on keys directly to the
    # backend and overriding the backend implementation.
    def set(self, key, value, **set_arguments):
        self.client.set(key, value, **set_arguments)

    def set_multi(self, mapping, **set_arguments):
        self.client.set_multi(mapping, **set_arguments)


# NOTE(morganfainberg): Redefine the basic backends from the
# dogpile.cache.backends.memcached module and use the
# :class:`MemcacheDriverMixin` to override the `set` and `set_multi` methods
# to allow explicit passing of the extra `set_arguments` to the client.
class Pylibmc(MemcachedDriverMixin, memcached.PylibmcBackend):
    pass


class BMemcached(MemcachedDriverMixin, memcached.BMemcachedBackend):
    pass


class Memcached(MemcachedDriverMixin, memcached.MemcachedBackend):
    pass


VALID_DOGPILE_BACKENDS = dict(Pylibmc=Pylibmc,
                              BMemcached=BMemcached,
                              Memcached=Memcached)


class MemcachedLock(object):
    """Simple distributed lock using memcached.

    This is an adaptation of the lock featured at
    http://amix.dk/blog/post/19386

    """

    def __init__(self, client_fn, key, lock_timeout, max_lock_attempts):
        self.client_fn = client_fn
        self.key = "_lock" + key
        self.lock_timeout = lock_timeout
        self.max_lock_attempts = max_lock_attempts

    def acquire(self, wait=True):
        client = self.client_fn()
        i = 0
        while True:
            if client.add(self.key, 1, self.lock_timeout):
                return True
            elif not wait:
                return False
            else:
                sleep_time = (((i + 1) * random.random()) + 2 ** i) / 2.5
                time.sleep(sleep_time)
            if i <= self.max_lock_attempts:
                i += 1
            else:
                raise exception.UnexpectedError(
                    _('Maximum lock attempts on %s occured.') % self.key)

    def release(self):
        client = self.client_fn()
        client.delete(self.key)


class MemcachedBackend(manager.Manager):
    """Pivot point to leverage the various dogpile.cache memcache backends.

    To specify a specific dogpile.cache memcached driver, pass the argument
    `memcache_driver` set to one of the provided memcache drivers (at this
    time `Memcached`, `BMemcached`, `Pylibmc` are valid).
    """
    def __init__(self, arguments):
        self.lock_timeout = arguments.pop('lock_timeout', None)
        self.max_lock_attempts = arguments.pop('max_lock_attempts', 15)
        # NOTE(morganfainberg): Remove distributed locking from the arguments
        # passed to the "real" backend if it exists.
        self._key_mangler = None
        self._raw_no_expiry_keys = set(arguments.pop('no_expiry_keys', []))
        self._no_expiry_keys = self._raw_no_expiry_keys
        self._set_arguments = {}
        if 'min_compress_len' in arguments:
            self._set_arguments['min_compress_len'] = \
                arguments['min_compress_len']
        if 'memcached_expire_time' in arguments:
            self._set_arguments['time'] = arguments['memcached_expire_time']
        backend = arguments.pop('memcached_driver', None)
        if 'url' not in arguments:
            # FIXME(morganfainberg): Log deprecation warning for old-style
            # configuration once full dict_config style configuration for
            # KVS backends is supported.  For now use the current memcache
            # section of the configuration.
            arguments['url'] = CONF.memcache.servers

        if backend is None:
            # NOTE(morganfainberg): Use the basic memcached backend if nothing
            # else is supplied.
            self.driver = Memcached(arguments)
        else:
            if backend not in VALID_DOGPILE_BACKENDS:
                raise ValueError(
                    _('Backend `%(driver)s` is not a valid memcached '
                      'backend. Valid drivers: %(driver_list)s') %
                    dict(driver=backend,
                         driver_list=','.join(VALID_DOGPILE_BACKENDS.keys())))
            else:
                self.driver = VALID_DOGPILE_BACKENDS[backend](arguments)

    def _get_set_arguments(self, exclude_expiry=False):
        set_arguments = self._set_arguments.copy()
        if exclude_expiry:
            # NOTE(morganfainberg): Explicitly strip out the 'time' key/value
            # from the set_arguments in the case that this key isn't meant to
            # expire.
            set_arguments.pop('time', None)

        return set_arguments

    def set(self, key, value):
        no_expiry = key in self._no_expiry_keys
        set_arguments = self._get_set_arguments(no_expiry)
        self.driver.set(key, value, **set_arguments)

    def set_multi(self, mapping):
        mapping_keys = set(mapping.keys())
        no_expiry_keys = mapping_keys.intersection(self._no_expiry_keys)
        has_expiry_keys = mapping_keys.difference(self._no_expiry_keys)

        if no_expiry_keys:
            new_mapping = dict((k, mapping[k]) for k in no_expiry_keys)
            set_arguments = self._get_set_arguments(exclude_expiry=True)
            self.driver.client.set_multi(new_mapping, **set_arguments)
        if has_expiry_keys:
            new_mapping = dict((k, mapping[k]) for k in has_expiry_keys)
            set_arguments = self._get_set_arguments(exclude_expiry=False)
            self.driver.client.set_multi(new_mapping, **set_arguments)

    @classmethod
    def from_config_dict(cls, config_dict, prefix):
        prefix_len = len(prefix)
        return cls(
            dict((key[prefix_len:], config_dict[key])
                 for key in config_dict
                 if key.startswith(prefix)))

    @property
    def key_mangler(self):
        if self._key_mangler is None:
            return self.driver.key_mangler
        return self._key_mangler

    @key_mangler.setter
    def key_mangler(self, key_mangler):
        if callable(key_mangler):
            self._key_mangler = key_mangler
            # NOTE(morganfainberg): Rehash all the non-expiring keys to the now
            # correct values via the key_mangler.
            no_expire = set()
            for key in self._raw_no_expiry_keys:
                no_expire.add(self._key_mangler(key))
            self._no_expiry_keys = no_expire
        elif key_mangler is None:
            self._no_expiry_keys = self._raw_no_expiry_keys
            pass
        else:
            raise TypeError(_('`key_mangler` functions must be callable.'))

    def get_mutex(self, key):
        return MemcachedLock(lambda: self.driver.client, key,
                             self.lock_timeout, self.max_lock_attempts)
