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
import copy

from dogpile.cache import proxy
from oslo_context import context as oslo_context


class _ResponseCacheProxy(proxy.ProxyBackend):

    __key_pfx = '_request_cache_%s'

    def _get_request_context(self):
        return oslo_context.get_current() or oslo_context.RequestContext()

    def _get_request_key(self, key):
        return self.__key_pfx % key

    def get(self, key):
        ctx = self._get_request_context()
        try:
            return copy.deepcopy(getattr(ctx, self._get_request_key(key)))
        except AttributeError:
            return self.proxied.get(key)

    def set(self, key, value):
        ctx = self._get_request_context()
        self.proxied.set(key, value)
        setattr(ctx, self._get_request_key(key), copy.deepcopy(value))
        ctx.update_store()

    def delete(self, key):
        ctx = self._get_request_context()
        try:
            delattr(ctx, self._get_request_key(key))
            ctx.update_store()
        except AttributeError:
            pass
        self.proxied.delete(key)

    def get_multi(self, keys):
        # NOTE(morganfainberg): get_multi is more expensive to use, but is
        # not used in keystone. This is for complete implementation to ensure
        # we don't bypass the local request cache by accident.
        values = []
        for key in keys:
            values.append(self.get(key))
        return keys

    def set_multi(self, mapping):
        # TODO(morganfainberg): Implement for completeness.
        self.proxied.set_multi(mapping)

    def delete_multi(self, keys):
        # TODO(morganfainberg): Implement for completeness.
        self.proxied.delete_multi(keys)
