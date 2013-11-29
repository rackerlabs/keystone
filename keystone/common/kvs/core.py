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

import threading

from dogpile.cache import api
from dogpile.cache import region
from dogpile.cache import util as dogpile_util
from dogpile.core import nameregistry

from keystone.common import config
from keystone import exception
from keystone.openstack.common import importutils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log
from keystoneclient.middleware import memcache_crypt


__all__ = ['KVSBase', 'KVSLock']


BACKENDS_REGISTERED = False
CONF = config.CONF
LOG = log.getLogger(__name__)
NO_VALUE = api.NO_VALUE


def _register_backends():
    # NOTE(morganfainberg): This function exists to ensure we do not try and
    # register the backends prior to the configuration object being fully
    # available.  We also need to ensure we do not register a given backend
    # more than one time.  All backends will be prefixed with openstack.kvs
    # as the "short" name to reference them for configuration purposes.
    global BACKENDS_REGISTERED

    if not BACKENDS_REGISTERED:
        prefix = 'openstack.kvs.%s'
        for backend in CONF.kvs.backends:
            module, cls = backend.rsplit('.', 1)
            backend_name = prefix % cls
            LOG.debug(_('Registering Dogpile Backend %(backend_path)s as '
                        '%(backend_name)s'), {'backend_path': backend,
                                              'backend_name': backend_name})
            region.register_backend(backend_name, module, cls)
        BACKENDS_REGISTERED = True


class KVSBase(object):
    """Basic KVS manager object to support Keystone Key-Value-Store systems.

    This manager also supports the concept of locking a given key resource to
    allow for a guaranteed atomic transaction to the backend.

    This KVS Backend Manager implements the ability to encrypt or validate
    data integrity from the various backends.  This is done via the
    memcache_crypt mechanism provided for keystoneclient.  No encryption
    or integrity validation will be performed unless explicitly configured to
    do so.  This means the crypto mechanisms have a dependency on pycrypto and
    will raise CryptoUnavailableError if pycrypto is unavailable and crypto
    is configured.
    """
    def __init__(self, name, security_strategy=None, secret_key=None,
                 key_mangler=None, proxy_list=None, **config_args):
        _register_backends()
        self.region_name = name
        self._key_mangler = key_mangler
        self._proxy_list = proxy_list
        self._security_strategy = security_strategy
        self._secret_key = secret_key

        self._region = region.make_region(name=self.region_name)
        self._configure_region(**config_args)
        self._lock_registry = nameregistry.NameRegistry(self._create_mutex)

        if self._security_strategy:
            if self._security_strategy not in ('MAC', 'ENCRYPT'):
                raise ValueError(_('`security_strategy` must be either `MAC` '
                                   'or `ENCRYPT`'))
            if not self._secret_key:
                raise ValueError(_('`security_strategy` is configured, '
                                   '`secret_key` must also be configured.'))

    def _apply_region_proxy(self):
        if self._proxy_list is not None:
            proxies = []
            region_proxy = self._proxy_list

            for class_path in region_proxy:
                cls = importutils.import_class(class_path)
                proxies.append((cls, class_path))

            for proxy, path in reversed(proxies):
                LOG.debug(_('Adding proxy \'%s\' to backend.'), path)
                self._region.wrap(proxy)

    def _build_crypto_info_from_key(self, key):
        # Encryption / MAC validation keys and cache_key derivation based upon
        # the secret_key and the targeted key to store the data at.
        c_keys = memcache_crypt.derive_keys(key, self._secret_key,
                                            self._security_strategy)
        cache_key = memcache_crypt.get_cache_key(c_keys)
        return c_keys, cache_key

    def _set_key_mangler(self):
        # Set the key_mangler that is appropriate for the given region being
        # configured here.  The key_mangler function is called prior to storing
        # the value(s) in the backend.  This is to help prevent collisions and
        # limit issues such as memcache's limited cache_key size.
        key_mangler = self._key_mangler
        use_backend_key_mangler = getattr(self._region.backend,
                                          'use_backend_key_mangler', False)
        if ((key_mangler is None or use_backend_key_mangler) and
                (self._region.backend.key_mangler is not None)):
            # NOTE(morganfainberg): Use the configured key_mangler as a first
            # choice. Second choice would be the key_mangler defined by the
            # backend itself.  Finally, fall back to the defaults.  The one
            # exception is if the backend defines `use_backend_key_mangler`
            # as True, which indicates the backend's key_mangler should be
            # the first choice.
            key_mangler = self._region.backend.key_mangler

        if self._security_strategy is not None:
            # If security strategy is enabled, we do not want any key_mangling
            # we will handle the key mangling at the KVSBase level.
            LOG.info(_('KVS security enabled with strategy: %s'),
                     self._security_strategy)
        elif CONF.kvs.enable_key_mangler:
            if key_mangler is not None:
                msg = _('Using %(func)s as KVS region %(name)s key_mangler')
                if callable(key_mangler):
                    self._region.key_mangler = key_mangler
                    LOG.info(msg, {'func': key_mangler.__name__,
                                   'name': self.region_name})
                elif isinstance(key_mangler, str):
                    module_str, func_str = key_mangler.rsplit('.', 1)
                    module = importutils.import_module(module_str)
                    func = getattr(module, func_str, None)
                    if callable(func):
                        self._region.key_mangler = func
                        LOG.info(msg, {'func': func.__name__,
                                       'name': self.region_name})

                if not self._region.key_mangler:
                    # NOTE(morganfainberg): We failed to set the key_mangler,
                    # we should error out here to ensure we aren't causing
                    # key-length or collision issues.
                    raise exception.ValidationError(
                        _('`key_mangler` option must be either a function '
                          'reference or a string for the function path '
                          '(e.g. module.submodule.function)'))
            else:
                LOG.info(_('Using default dogpile sha1_mangle_key as KVS '
                           'region %s key_mangler'), self.region_name)
                # NOTE(morganfainberg): Sane 'default' keymangler is the
                # dogpile sha1_mangle_key function.  This ensures that unless
                # explicitly changed, we mangle keys.  This helps to limit
                # unintended cases of exceeding cache-key in backends such
                # as memcache.
                self._region.key_mangler = dogpile_util.sha1_mangle_key
        else:
            LOG.info(_('KVS region %s key_mangler disabled.'),
                     self.region_name)

    def _configure_region(self, **config_args):
        prefix = CONF.kvs.config_prefix
        if 'backend' not in config_args:
            raise exception.ValidationError(_('`backend` is a required '
                                              'argument for KVS '
                                              'configuration.'))

        conf_dict = {}
        conf_dict['%s.backend' % prefix] = config_args.pop('backend')
        for argument, value in config_args.iteritems():
            arg_key = '.'.join([prefix, 'arguments', argument])
            conf_dict[arg_key] = value
        if 'backend' in self._region.__dict__:
            # NOTE(morganfainberg): It is a bad idea to reconfigure a backend,
            # there are a lot of pitfalls and potential memory leaks that could
            # occur.  By far the best approach is to re-create the KVS object
            # with the new configuration.
            LOG.warning(_('KVS region %s is already configured. '
                          'Cannot reconfigure.'), self.region_name)
        else:
            LOG.debug(_('KVS region configuration for %(name)s: %(config)r'),
                      {'name': self.region_name,
                       'config': conf_dict})
            self._region.configure_from_config(conf_dict, '%s.' % prefix)
            self._set_key_mangler()
            self._apply_region_proxy()

    def _mutex(self, key):
        return self._lock_registry.get(key)

    def _create_mutex(self, key):
        mutex = self._region.backend.get_mutex(key)
        if mutex is not None:
            return mutex
        else:
            return self._LockWrapper()

    class _LockWrapper(object):
        """weakref-capable threading.Lock wrapper."""
        def __init__(self):
            self.lock = threading.Lock()

        def acquire(self, wait=True):
            return self.lock.acquire(wait)

        def release(self):
            self.lock.release()

    def _get(self, key):
        if self._security_strategy is None:
            data = self._region.get(key)
        else:
            c_keys, cache_key = self._build_crypto_info_from_key(key)
            raw_data = self._region.get(cache_key)
            try:
                if raw_data is not NO_VALUE:
                    # unprotect data will return None if raw_data is None
                    data = memcache_crypt.unprotect_data(c_keys, raw_data)
                else:
                    data = NO_VALUE
            except Exception as e:
                # NOTE(morganfainberg): All exceptions are an error that need
                # to be logged.  This data is bad.  In cases such as this we
                # will specifically pass back the NO_VALUE (empty data) value
                msg = _('Failed to decrypt/verify data from KVS: %s')
                LOG.error(msg, e)
                data = NO_VALUE

            if data is not NO_VALUE:
                data = jsonutils.loads(data)

        return data

    def _set(self, key, value, c_keys):
        if c_keys is not None:
            serialized_data = jsonutils.dumps(value)
            value = memcache_crypt.protect_data(c_keys, serialized_data)
        self._region.set(key, value)

    def get(self, key):
        """Get a single value from the KVS backend."""
        value = self._get(key)
        if value is NO_VALUE:
            raise exception.NotFound(target=key)
        return value

    def get_multi(self, keys):
        """Get multiple values in a single call from the KVS backend."""
        if self._security_strategy is None:
            values = self._region.get_multi(keys)
        else:
            # NOTE(morganfainberg): Since we have a security strategy, we will
            # use the KVSBase mechanism to unprotect the data.  This is
            # likely less performant than allowing the backend to use it's
            # get_multi implementation, however this reduces code duplication
            # in a clean and maintainable way.
            values = [self._get(key) for key in keys]

        not_found = []
        for index, key in enumerate(keys):
            if values[index] is NO_VALUE:
                not_found.append(key)

        if not_found:
            raise exception.NotFound(target=not_found)

        return values

    def get_and_set(self, key, callback):
        """A method to perform a get, use that data and perform a set based
        upon the results of a callback method in a single transaction.

        KVSBase will perform a get and feed the results of that get into the
        callback utilizing the locking mechanism of KVSBase to ensure that
        all similar calls will be serialized.
        """
        if not callable(callback):
            raise TypeError(_('callback must be a callable type, got: %s') %
                            type(callback))

        if self._security_strategy is not None:
            c_keys, backend_key = self._build_crypto_info_from_key(key)
        else:
            if self._region.key_mangler is not None:
                backend_key = key

            c_keys = None

        with KVSLock(self._mutex(backend_key), backend_key):
            get_data = self._get(backend_key)
            if get_data is NO_VALUE:
                get_data = None
            value = callback(get_data)
            self._set(backend_key, value, c_keys)

    def set(self, key, value):
        """Set a single value in the KVS backend."""
        if self._security_strategy is not None:
            c_keys, key = self._build_crypto_info_from_key(key)
        else:
            c_keys = None

        with KVSLock(self._mutex(key), key):
            self._set(key, value, c_keys)

    def set_multi(self, mapping):
        """Set multiple key/value pairs in the KVS backend at once.

        Each individual set is serialized/locked via KVSLock mechanism.
        """
        # NOTE(morganfainberg): Due to serialization needs, it is
        # easier to prevent duplicated code here by calling the
        # manager's `set` method rather than relying on the backend to
        # do the multi_set directly. This will be slightly less efficient.
        for k, v in mapping.iteritems():
            self.set(k, v)

    def delete(self, key):
        """Delete a single key from the KVS backend.

        This method will raise NotFound if the key doesn't exist.  The get and
        delete are done in a single transaction (via KVSLock mechanism).
        """
        delete_key = key
        if self._security_strategy is not None:
            c_keys, delete_key = self._build_crypto_info_from_key(key)

        with KVSLock(self._mutex(delete_key), delete_key):
            # NOTE(morganfainberg): Always perform a "get" to make sure
            # the value(s) exist before deletion.  This needs to be done
            # in the context of a KVSLock to limit races. This context
            # manager may not be strictly required.
            self.get(key)
            self._region.delete(delete_key)

    def delete_multi(self, keys):
        """Delete multiple keys from the KVS backend in a single call."""
        if self._security_strategy is None:
            self._region.delete_multi(keys)
        else:
            # NOTE(morganfainberg): Since there is no deserialization needed
            # here, we will build the key-list first, then (possibly) let the
            # backend perform whatever optimisations it can on a delete_multi
            # call.
            to_delete = []
            for key in keys:
                c_keys, delete_key = self._build_crypto_info_from_key(key)
                to_delete.append(delete_key)
            self._region.delete_multi(to_delete)


class KVSLock(object):
    """Basic KVSLock context manager that hooks into the dogpile.cache
    backend mutex allowing for distributed locking on resources.
    """
    def __init__(self, mutex, key):
        self.mutex = mutex
        self.key = key

    def acquire(self):
        if CONF.kvs.enable_locking:
            self.mutex.acquire()
            LOG.debug(_('KVS lock acquired for: %s'), self.key)

    __enter__ = acquire

    def release(self):
        if CONF.kvs.enable_locking:
            self.mutex.release()
            LOG.debug(_('KVS lock released for: %s'), self.key)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
