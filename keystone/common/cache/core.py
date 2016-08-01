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

import functools
import uuid

import dogpile.cache
import dogpile.cache.region
from oslo_cache import core as cache

from keystone.common.cache import _context_cache
import keystone.conf


CONF = keystone.conf.CONF


class CacheRegion(dogpile.cache.CacheRegion):

    REGION_KEY_PREFIX = '<<<region>>>:'

    @property
    def region_key(self):
        return self.REGION_KEY_PREFIX + self.name

    @property
    def region_id(self):
        value = self.backend.get(self.region_key)
        if not value:
            value = uuid.uuid4().hex
            # TODO(dstanek): this should last forever
            self.backend.set(self.region_key, value)
        return value

    def invalidate(self):
        new_region_id = uuid.uuid4().hex
        # TODO(dstanek): this should last forever
        self.backend.set(self.region_key, new_region_id)


dogpile.cache.CacheRegion = CacheRegion
dogpile.cache.region.CacheRegion = CacheRegion


class KeyMangler(object):

    REGION_KEY_PREFIX = '<<<region>>>:'

    def __init__(self, region):
        self._region = region

    @property
    def region_key(self):
        return self.REGION_KEY_PREFIX + self._region.name

    @property
    def region_id(self):
        value = self._region.backend.get(self.region_key)
        if not value:
            value = uuid.uuid4().hex
            # TODO(dstanek): this should last forever
            self._region.backend.set(self.region_key, value)
        return value

    def __call__(self, key):
        if key != self.region_key:
            key = '%s:%s' % (key, self.region_id)
        return cache._sha1_mangle_key(key)


def create_region(name):
    """Create a dopile region.

    Wraps oslo_cache.core.create_region. This is used to ensure that the
    Region is properly patched and allows us to more easily specify a region
    name.

    :param str name: The region name
    :returns: The new region.
    :rtype: :class:`dogpile.cache.region.CacheRegion`

    """
    region = cache.create_region()
    region.name = name  # oslo.cache doesn't allow this yet
    return region


CACHE_REGION = create_region(name='shared default')

register_model_handler = _context_cache._register_model_handler


def configure_cache(region=None):
    if region is None:
        region = CACHE_REGION
    # NOTE(morganfainberg): running cache.configure_cache_region()
    # sets region.is_configured, this must be captured before
    # cache.configure_cache_region is called.
    configured = region.is_configured
    cache.configure_cache_region(CONF, region)
    # Only wrap the region if it was not configured. This should be pushed
    # to oslo_cache lib somehow.
    if not configured:
        region.wrap(_context_cache._ResponseCacheProxy)
        region.key_mangler = KeyMangler(region)


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
