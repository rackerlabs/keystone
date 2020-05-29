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

import keystone.conf


CONF = keystone.conf.CONF


def symptom_caching_disabled():
    """`keystone.conf [cache] enabled` is not enabled.

    Caching greatly improves the performance of keystone, and it is highly
    recommended that you enable it.
    """
    return not CONF.cache.enabled


def symptom_caching_enabled_without_a_backend():
    """Caching is not completely configured.

    Although caching is enabled in `keystone.conf [cache] enabled`, the default
    backend is still set to the no-op backend. Instead, configure keystone to
    point to a real caching backend like memcached.
    """
    return CONF.cache.enabled and CONF.cache.backend == 'dogpile.cache.null'


def symptom_caching_debug_log_enabled():
    """Enabling caching log is not completely configured.

    Although debug level is enabled for Keystone, it's needed to enabled debug
    level for the cache backend to be able to see the caching debug logs on the
    Keystone logs files.
    """
    return (CONF.debug and CONF.cache.enabled
            and CONF.cache.debug_cache_backend and (
                'oslo.cache=DEBUG' and
                'dogpile.core.dogpile=DEBUG' in CONF.default_log_levels))
