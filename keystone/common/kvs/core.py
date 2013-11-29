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

import contextlib
import threading
import time
import weakref

from dogpile.cache import api
from dogpile.cache import proxy
from dogpile.cache import region
from dogpile.cache import util as dogpile_util
from dogpile.core import nameregistry

from keystone.common import config
from keystone import exception
from keystone.openstack.common import importutils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log
from keystoneclient.middleware import memcache_crypt


__all__ = ['KeyValueStore', 'KeyValueStoreLock', 'LockTimeout',
           'get_key_value_store']


BACKENDS_REGISTERED = False
CONF = config.CONF
KEY_VALUE_STORE_REGISTRY = weakref.WeakValueDictionary()
LOCK_WINDOW = 1
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


class LockTimeout(exception.UnexpectedError):
    message_format = _('Lock Timeout occurred for key, %(target)s')


class KeyValueStore(object):
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
    def __init__(self, kvs_region):
        self.locking = True
        self._region = kvs_region
        self._security_strategy = None
        self._secret_key = None
        self._lock_registry = nameregistry.NameRegistry(self._create_mutex)

    def configure(self, backing_store, security_strategy=None, secret_key=None,
                  key_mangler=None, proxy_list=None, locking=True,
                  **region_config_args):
        """Configure the KeyValueStore instance.

        :param backing_store: dogpile.cache short name of the region backend
        :param security_strategy: (optional) ENCRYPT or MAC
        :param secret_key: (optional) secret key for security_strategy
        :param key_mangler: key_mangler function
        :param proxy_list: list of proxy classes to apply to the region
        :param locking: boolean that allows disabling of locking mechanism for
                        this instantiation
        :param region_config_args: key-word args passed to the dogpile.cache
                                   backend for configuration
        :return:
        """
        if 'backend' in self._region.__dict__:
            # NOTE(morganfainberg): It is a bad idea to reconfigure a backend,
            # there are a lot of pitfalls and potential memory leaks that could
            # occur.  By far the best approach is to re-create the KVS object
            # with the new configuration.
            raise RuntimeError(_('KVS region %s is already configured. '
                                 'Cannot reconfigure.') % self._region.name)

        self.locking = locking
        if security_strategy:
            if not secret_key:
                raise ValueError(_('`security_strategy` is defined, '
                                   '`secret_key` must also be defined.'))
            if security_strategy not in ('MAC', 'ENCRYPT'):
                raise ValueError(_('`security_strategy` must be either '
                                   '`MAC` or `ENCRYPT`'))
            self._security_strategy = security_strategy
            self._secret_key = secret_key
        self._configure_region(backing_store, **region_config_args)
        self._set_key_mangler(key_mangler)
        self._apply_region_proxy(proxy_list)

    def _apply_region_proxy(self, proxy_list):
        if getattr(proxy_list, '__iter__', False):
            proxies = []

            for item in proxy_list:
                if isinstance(item, str):
                    LOG.debug(_('Importing class %s as KVS proxy.') % item)
                    pxy = importutils.import_class(item)
                else:
                    pxy = item

                if issubclass(pxy, proxy.ProxyBackend):
                    proxies.append(pxy)
                else:
                    LOG.warning(_('%s is not a dogpile.proxy.ProxyBackend'),
                                pxy.__name__)

            for proxy_cls in reversed(proxies):
                LOG.info(_('Adding proxy \'%(proxy)s\' to KVS %(name)s.'),
                         {'proxy': proxy_cls.__name__,
                          'name': self._region.name})
                self._region.wrap(proxy_cls)

    def _build_crypto_info_from_key(self, key):
        # Encryption / MAC validation keys and cache_key derivation based upon
        # the secret_key and the targeted key to store the data at.
        c_keys = memcache_crypt.derive_keys(key, self._secret_key,
                                            self._security_strategy)
        cache_key = memcache_crypt.get_cache_key(c_keys)
        return c_keys, cache_key

    def _set_key_mangler(self, key_mangler):
        # Set the key_mangler that is appropriate for the given region being
        # configured here.  The key_mangler function is called prior to storing
        # the value(s) in the backend.  This is to help prevent collisions and
        # limit issues such as memcache's limited cache_key size.
        key_mangler = key_mangler
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
            # we will handle the key mangling at the KeyValueStore level.
            LOG.info(_('KVS security enabled with strategy: %s'),
                     self._security_strategy)
        elif CONF.kvs.enable_key_mangler:
            if key_mangler is not None:
                msg = _('Using %(func)s as KVS region %(name)s key_mangler')
                if callable(key_mangler):
                    self._region.key_mangler = key_mangler
                    LOG.info(msg, {'func': key_mangler.__name__,
                                   'name': self._region.name})
                elif isinstance(key_mangler, str):
                    module_str, func_str = key_mangler.rsplit('.', 1)
                    module = importutils.import_module(module_str)
                    func = getattr(module, func_str, None)
                    if callable(func):
                        self._region.key_mangler = func
                        LOG.info(msg, {'func': func.__name__,
                                       'name': self._region.name})

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
                           'region %s key_mangler'), self._region.name)
                # NOTE(morganfainberg): Sane 'default' keymangler is the
                # dogpile sha1_mangle_key function.  This ensures that unless
                # explicitly changed, we mangle keys.  This helps to limit
                # unintended cases of exceeding cache-key in backends such
                # as memcache.
                self._region.key_mangler = dogpile_util.sha1_mangle_key
        else:
            LOG.info(_('KVS region %s key_mangler disabled.'),
                     self._region.name)

    def _configure_region(self, backend, **config_args):
        prefix = CONF.kvs.config_prefix
        conf_dict = {}
        conf_dict['%s.backend' % prefix] = backend

        if 'distributed_lock' not in config_args:
            config_args['distributed_lock'] = True

        if 'lock_timeout' not in config_args:
            config_args['lock_timeout'] = CONF.kvs.default_lock_timeout

        # NOTE(morganfainberg): To mitigate race conditions on comparing
        # the timeout and current time on the lock mutex, we are building
        # in a static 1 second overlap where the lock will still be valid
        # in the backend but not from the perspective of the context
        # manager.  Since we must develop to the lowest-common-denominator
        # when it comes to the backends, memcache's cache store is not more
        # refined than 1 second, therefore we must build in at least a 1
        # second overlap.  `lock_timeout` of 0 means locks never expire.
        if config_args['lock_timeout'] > 0:
            config_args['lock_timeout'] += LOCK_WINDOW

        for argument, value in config_args.iteritems():
            arg_key = '.'.join([prefix, 'arguments', argument])
            conf_dict[arg_key] = value

        LOG.debug(_('KVS region configuration for %(name)s: %(config)r'),
                  {'name': self._region.name,
                   'config': conf_dict})
        self._region.configure_from_config(conf_dict, '%s.' % prefix)

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
            self.lock_timeout = CONF.kvs.default_lock_timeout - 1

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

    def _set(self, key, value):
        if self._security_strategy is not None:
            c_keys, key = self._build_crypto_info_from_key(key)
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
            # use the KeyValueStore mechanism to unprotect the data.  This is
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

    def set(self, key, value, lock=None):
        """Set a single value in the KVS backend."""
        with self._action_with_lock(key, lock):
            self._set(key, value)

    def set_multi(self, mapping):
        """Set multiple key/value pairs in the KVS backend at once.

        Like delete_multi, this call does not serialize through the
        KeyValueStoreLock mechanism (locking cannot occur on more than one
        key in a given context without significant deadlock potential).
        """
        if self._security_strategy is None:
            self._region.set_multi(mapping)
        else:
            # NOTE(morganfainberg): Due to serialization needs, it is
            # easier to prevent duplicated code here by calling the
            # manager's `set` method rather than relying on the backend to
            # do the multi_set directly. This will be slightly less efficient.
            for k, v in mapping.iteritems():
                self._set(k, v)

    def delete(self, key, lock=None):
        """Delete a single key from the KVS backend.

        This method will raise NotFound if the key doesn't exist.  The get and
        delete are done in a single transaction (via KeyValueStoreLock
        mechanism).
        """
        delete_key = key
        if self._security_strategy is not None:
            c_keys, delete_key = self._build_crypto_info_from_key(key)

        with self._action_with_lock(delete_key, lock):
            # NOTE(morganfainberg): Always perform a "get" to make sure
            # the value(s) exist before deletion.  This needs to be done
            # in the context of a KeyValueStoreLock to limit races. This
            # context manager may not be strictly required.
            self.get(key)
            self._region.delete(delete_key)

    def delete_multi(self, keys):
        """Delete multiple keys from the KVS backend in a single call.

        Like set_multi, this call does not serialize through the
        KeyValueStoreLock mechanism (locking cannot occur on more than one
        key in a given context without significant deadlock potential).
        """
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

    def get_lock(self, key):
        """Get a write lock on the KVS value referenced by `key`.

        The ability to get a context manager to pass into the set/delete
        methods allows for a single-transaction to occur while guaranteeing the
        backing store will not change between the start of the 'lock' and the
        end.  Lock timeout is fixed to the KeyValueStore configured lock
        timeout.
        """
        return KeyValueStoreLock(self._mutex(key), key, self.locking)

    @contextlib.contextmanager
    def _action_with_lock(self, key, lock=None):
        """Wrapper context manager to create a lock if one has not been
        passed into the action method (set/delete/etc).
        """
        if not isinstance(lock, KeyValueStoreLock):
            lock = self.get_lock(key)

        if not lock.key == key:
            raise ValueError(_('Lock key must match target key: %(lock)s '
                               '!= %(target)s') % {'lock': lock.key,
                                                   'target': key})
        if lock.active:
            if not lock.expired:
                yield
            else:
                raise LockTimeout(target=key)
        else:
            with lock:
                # NOTE(morganfainberg): It is possible to still race in some
                # conditions here.  But that would be due to a significant
                # delay in communicating with the backend.  Likely that will
                # cause other issues than just odd-lock behavior.
                yield


class KeyValueStoreLock(object):
    """Basic KeyValueStoreLock context manager that hooks into the
    dogpile.cache backend mutex allowing for distributed locking on resources.

    This is only a write lock, and will not prevent reads from occurring.
    """
    def __init__(self, mutex, key, locking_enabled=True):
        self.mutex = mutex
        self.key = key
        self.enabled = locking_enabled
        self.active = False
        self.acquire_time = 0

    def acquire(self):
        if self.enabled:
            self.mutex.acquire()
            LOG.debug(_('KVS lock acquired for: %s'), self.key)
        self.active = True
        self.acquire_time = time.time()
        return self

    __enter__ = acquire

    @property
    def expired(self):
        if self.mutex.lock_timeout == 0:
            return False
        else:
            calculated = time.time() - self.acquire_time + LOCK_WINDOW
            return calculated > self.mutex.lock_timeout

    def release(self):
        if self.enabled:
            self.mutex.release()
            if self.expired:
                LOG.debug(_('KVS lock released for: %s'), self.key)
            else:
                LOG.warning(_('KVS lock released (timeout reached) for: %s'),
                            self.key)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def get_key_value_store(name, kvs_region=None):
    """Instantiate a new :class:`.KeyValueStore` or return a previous
    instantiation that has the same name.
    """
    global KEY_VALUE_STORE_REGISTRY

    _register_backends()
    key_value_store = KEY_VALUE_STORE_REGISTRY.get(name)
    if key_value_store is None:
        if kvs_region is None:
            kvs_region = region.make_region(name=name)
        key_value_store = KeyValueStore(kvs_region)
        KEY_VALUE_STORE_REGISTRY[name] = key_value_store
    return key_value_store
