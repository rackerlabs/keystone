# Copyright 2013 Metacloud
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

"""Keystone Caching Layer Implementation."""
import hashlib
import time

import dogpile.cache
from dogpile.cache import api
from dogpile.cache import proxy
from oslo_cache import core as cache
from oslo_config import cfg

CONF = cfg.CONF
CACHE_REGION = cache.create_region()


def configure_cache(region=None):
    if region is None:
        region = CACHE_REGION
    cache.configure_cache_region(CONF, region)


def get_memoization_decorator(group, expiration_group=None, region=None):
    if region is None:
        region = CACHE_REGION
    return cache.get_memoization_decorator(CONF, region, group,
                                           expiration_group=expiration_group)


# NOTE(stevemar): When memcache_pool, mongo and noop backends are removed
# we no longer need to register the backends here.
dogpile.cache.register_backend(
    'keystone.common.cache.noop',
    'keystone.common.cache.backends.noop',
    'NoopCacheBackend')

dogpile.cache.register_backend(
    'keystone.cache.mongo',
    'keystone.common.cache.backends.mongo',
    'MongoCacheBackend')

dogpile.cache.register_backend(
    'keystone.cache.memcache_pool',
    'keystone.common.cache.backends.memcache_pool',
    'PooledMemcachedBackend')


# TODO(morganfainberg): Move this logic up into oslo.cache directly
# so we can handle region-wide invalidations or alternatively propose
# a fix to dogpile.cache to make region-wide invalidates possible to
# work across distributed processes.
class _RegionInvalidateProxy(proxy.ProxyBackend):
    """A CacheProxy that enabled cross-process region-wide invalidation.

    In a distributed system, it is not currently possible to do a region-wide
    invalidation without it being isolated to a given process. This proxy
    is a baseclass that is a helper to change the expiration passed up from
    the backend in the same way that the
    class:`dogpile.cache.CacheRegion` `invalidate` method works.
    """

    @property
    def expiration_region_key(self):
        # NOTE(morganfainberg): Do not use this proxy without actually
        # defining the proper key. This is not meant to be used directly,
        # use `apply_invalidation_proxy()`.
        raise NotImplementedError()

    @@property
    def _region(self):
        # NOTE(morganfainberg): we need the region to be set, since
        # invalidate needs to set a key, rather than re-implementing
        # the logic the region implements, just call the region's set.
        # Be sure to use `apply_invalidation_proxy`
        raise NotImplementedError()

    def get(self, key):
        """Check the invalidated time key and override if appropriate."""
        value = super(_RegionInvalidateProxy, self).get(key)
        invalidated_time = super(_RegionInvalidateProxy, self).get(
            self.expiration_region_key)
        # NOTE(morganfainberg): Check to see if the value's creation time
        # is older than the invalidated time, return NO_VALUE as if the
        # item from cache is no longer available
        if (value is not api.NO_VALUE and
                value.metadata['ct'] < invalidated_time):
            return api.NO_VALUE
        return value

    def get_multi(self, keys):
        """Check the invalidated time key and override if appropriate."""
        values = super(_RegionInvalidateProxy, self).get_multi(keys)
        invalidated_time = super(_RegionInvalidateProxy, self).get(
            self.expiration_region_key)
        for idx, value in enumerate(values):
            # NOTE(morganfainberg): Check to see if the value's creation time
            # is older than the invalidated time, return NO_VALUE as if the
            # item from cache is no longer available.
            if (value is not api.NO_VALUE and
                    value.metadata['ct'] < invalidated_time):
                values[idx] = api.NO_VALUE
        return values

    def invalidate(self):
        self._region.set(self.expiration_region_key, time.time())


def apply_invalidation_proxy(region, region_name):
    """Construct proxy with the region name defined and apply to the region"""
    hasher = hashlib.sha1()
    hasher.update('_RegionExpiration.%s' % region_name)

    class InvalidationProxy(_RegionInvalidateProxy):
        expiration_region_key = hasher.hexdigest()

    proxy = InvalidationProxy()
    region.wrap(proxy)
    setattr(region, "invalidate", proxy.invalidate)
    setattr(proxy, '_region', region)
