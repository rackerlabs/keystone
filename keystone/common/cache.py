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

"""Keystone Caching Implementation."""

import dogpile.cache
from dogpile.cache import proxy

from keystone.common import config
from keystone.common import logging
from keystone.openstack.common import importutils


CONF = config.CONF
LOG = logging.getLogger(__name__)


class CacheDisableProxy(proxy.ProxyBackend):
    """Proxy Cache Wrapper that will disable all caching."""
    def set(self, key, value):
        # do not perform a set on the back end.
        return

    def set_multi(self, mapping):
        # do not perform a multi-set on the back end.
        return


def build_cache_config():
    prefix = CONF.cache.config_prefix
    conf_dict = {}
    conf_dict['%s.backend' % prefix] = CONF.cache.backend
    conf_dict['%s.expiration_time' % prefix] = CONF.cache.expiration_time
    for argument in CONF.cache.backend_argument:
        try:
            (argname, argvalue) = argument.split(':', 1)
        except ValueError:
            msg = _('Unable to build cache config key. Expected format '
                    '"<argname>:<value>". Skipping unknown format: %s')
            LOG.error(msg % argument)
            continue

        arg_key = '.'.join([prefix, 'arguments', argname])
        conf_dict[arg_key] = argvalue

    return conf_dict


def build_cache_region():
    region = dogpile.cache.make_region()
    config_dict = build_cache_config()
    region.configure_from_config(config_dict, '%s.' % CONF.cache.config_prefix)

    if not CONF.cache.enable:
        # NOTE(morganfainberg): Use a proxy to disable "sets". This might be
        # better to make a wrapper function that passes in should_cache_fn into
        # the decorator. For a first pass, this solves the same need, but
        # doesn't prevent the use of "should_cache_fn" in any given case.
        region.wrap(CacheDisableProxy)

    for class_path in CONF.cache.cache_proxies:
        # NOTE(morganfainberg): if we have any proxy wrappers, we should ensure
        # they are added to the cache region's backend.  Since
        # configure_from_config doesn't handle the wrap argument, we need to
        # manually add the Proxies. For information on how the ProxyBackends
        # work, see the dogpile.cache documents on "changing-backend-behavior"
        cls = importutils.import_class(class_path)
        LOG.debug(_('Adding cache-proxy \'%s\' to backend.') % class_path)
        region.wrap(cls)

    return region

REGION = build_cache_region()
on_arguments = REGION.cache_on_arguments
