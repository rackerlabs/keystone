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

"""A dogpile.cache proxy that caches objects in the request local cache."""

import copy

from dogpile.cache import proxy
from osprofiler import profiler


class _ProfileCacheProxy(proxy.ProxyBackend):

    __cache_type_prefix__ = "%s"

    def get(self, key):
        with profiler.Trace(self.__cache_type_prefix__ % "cache_get",
                            info={"key": key}):
            return self.proxied.get(key)

    def set(self, key, value):
        with profiler.Trace(self.__cache_type_prefix__ % "cache_set",
                            info={"key": key, "value": value}):
            self.proxied.set(key, value)

    def delete(self, key):
        with profiler.Trace(self.__cache_type_prefix__ % "cache_delete",
                            info={"key": key}):
            self.proxied.delete(key)

    def get_multi(self, keys):
        with profiler.Trace(self.__cache_type_prefix__ % "cache_get_multi",
                            info={"key": keys}):
            return self.proxied.get_multi(keys)

    def set_multi(self, mapping):
        with profiler.Trace(self.__cache_type_prefix__ % "cache_set_multi",
                            info={"key": mapping}):
            self.proxied.set_multi(mapping)

    def delete_multi(self, keys):
        with profiler.Trace(self.__cache_type_prefix__ % "cache_delete_multi",
                            info={"key": keys}):
            self.proxied.delete_multi(keys)


def get_profile_proxy(cache_type):
    proxy = type('_ProfileCacheProxySpecified',
                 _ProfileCacheProxy.__bases__,
                 dict(_ProfileCacheProxy.__dict__))
    proxy.__cache_type_prefix__ = cache_type

    return proxy
