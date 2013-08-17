# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import dogpile.cache

from dogpile.cache import proxy

from keystone.common import config
from keystone.common import logging
from keystone import exception
from keystone.openstack.common import importutils


CONF = config.CONF
LOG = logging.getLogger(__name__)
REGION = dogpile.cache.make_region()

dogpile.cache.register_backend(
    'keystone.common.cache.noop',
    'keystone.common.cache.backends.noop',
    'NoopCacheBackend')


class DebugProxy(proxy.ProxyBackend):
    """Extra Logging ProxyBackend."""
    def get(self, key):
        value = self.proxied.get(key)
        msg = _('CACHE_GET: Key: "%(key)s)" "%(value)s"')
        LOG.debug(msg % {'key': key, 'value': value})
        return value

    def get_multi(self, keys):
        values = self.proxied.get_multi(keys)
        msg = _('CACHE_GET_MULTI: "%(key)s" "%(value)s"')
        LOG.debug(msg % {'keys': keys, 'values': values})
        return values

    def set(self, key, value):
        msg = _('CACHE_SET: Key: %(key)s Value: %(value)s')
        LOG.debug(msg % {'key': key, 'value': value})
        return self.proxied.set(key, value)

    def set_multi(self, keys):
        LOG.debug(_('CACHE_SET_MULTI: %s') % keys)
        self.proxied.set_multi(keys)

    def delete(self, key):
        self.proxied.delete(key)
        LOG.debug(_('CACHE_DELETE: %s') % key)

    def delete_multi(self, keys):
        LOG.debug(_('CACHE_DELETE_MULTI: %s') % keys)
        self.proxied.delete_multi(keys)


def build_cache_config(conf):
    """Build the cache region dictionary configuration.

    :param conf: configuration object for keystone
    :returns: dict
    """
    prefix = conf.cache.config_prefix
    conf_dict = {}
    conf_dict['%s.backend' % prefix] = conf.cache.backend
    conf_dict['%s.expiration_time' % prefix] = conf.cache.expiration_time
    conf_dict['%s.key_mangler' % prefix] = conf.cache.key_mangler
    for argument in conf.cache.backend_argument:
        try:
            (argname, argvalue) = argument.split(':', 1)
        except ValueError:
            msg = _('Unable to build cache config-key. Expected format '
                    '"<argname>:<value>". Skipping unknown format: %s')
            LOG.error(msg, argument)
            continue

        arg_key = '.'.join([prefix, 'arguments', argname])
        conf_dict[arg_key] = argvalue

        LOG.debug(_('Keystone Cache Config: %s'), conf_dict)

    return conf_dict


def configure_cache_region(conf, region=None):
    """Configure a cache region."""
    if region is None:
        region = dogpile.cache.make_region()
    elif (isinstance(region, dogpile.cache.CacheRegion) and
          'backend' in region.__dict__):
        # NOTE(morganfainberg): this is how you tell if a region is configured.
        # There is an upstream issue requesting an enhancement to better
        # determine if the CacheRegion is configured
        return region

    config_dict = build_cache_config(conf)

    region.configure_from_config(config_dict, '%s.' % conf.cache.config_prefix)

    if conf.cache.verbose:
        region.wrap(DebugProxy)

    for class_path in conf.cache.proxies:
        # NOTE(morganfainberg): if we have any proxy wrappers, we should ensure
        # they are added to the cache region's backend.  Since
        # configure_from_config doesn't handle the wrap argument, we need to
        # manually add the Proxies. For information on how the ProxyBackends
        # work, see the dogpile.cache documents on "changing-backend-behavior"
        cls = importutils.import_class(class_path)
        LOG.debug(_('Adding cache-proxy \'%s\' to backend.') % class_path)
        region.wrap(cls)

    return region


def should_cache_fn(section):
    """Build a function that returns a config section's caching status.

    For any given driver in keystone that has caching capabilities, a boolean
    config option for that driver's section (e.g. ``token``) should exist and
    default to ``True``.  This function will use that value to tell the caching
    decorator if caching for that driver is enabled.  To properly use this
    with the decorator, pass this function the configuration section and assign
    the result to a variable.  Pass the new variable to the caching decorator
    as the named argument ``should_cache_fn``.  e.g.:

        from keystone.common import cache

        SHOULD_CACHE = cache.should_cache_fn('token')

        @cache.on_arguments(should_cache_fn=SHOULD_CACHE)
        def function(arg1, arg2):
            ...

    :param section: name of the configuration section to examine
    :type section: string
    :returns: function reference
    """
    def should_cache(value):
        if not CONF.cache.enable:
            return False
        conf_group = getattr(CONF, section)
        return getattr(conf_group, 'caching', True)
    return should_cache


on_arguments = REGION.cache_on_arguments
