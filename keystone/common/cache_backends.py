# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

"""Keystone Caching Backend Class Definitions."""

from dogpile.cache import api
from dogpile.cache import proxy

NO_VALUE = api.NO_VALUE


# FIXME(morganfainberg): Look at moving contents of this file into
# keystone.common.cache if possible
class BypassCacheProxy(proxy.ProxyBackend):
    """Proxy Cache Wrapper that will disable all caching."""
    def set(self, key, value):
        # do not perform a set on the back end.
        return

    def set_multi(self, mapping):
        # do not perform a multi-set on the back end.
        return


class NoopCache(api.CacheBackend):
    """A cache backend that does nothing.

    This backend is designed to incur the lowest overhead possible for the
    default behavior when dealing with the caching layer.
    """
    def __init__(self, arguments):
        return

    def get(self, key):
        return NO_VALUE

    def get_multi(self, keys):
        return [NO_VALUE for key in keys]

    def set(self, key, value):
        return

    def set_multi(self, mapping):
        return

    def delete(self, key):
        return

    def delete_multi(self, keys):
        return
