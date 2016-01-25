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
from dogpile.cache import api
from dogpile.cache import proxy
from oslo_context import context as oslo_context
from oslo_serialization import msgpackutils

from keystone.models import revoke_model


class _RevokeModelHandler(object):
    # NOTE(morganfainberg): There needs to be reserved "registry" entries set
    # in oslo_serialization for application-specific handlers. We picked 127
    # here since it's waaaaaay far out before oslo_serialization will use it.
    identity = 127
    handles = (revoke_model.RevokeTree,)

    def __init__(self, registry):
        self._registry = registry

    def serialize(self, obj):
        return msgpackutils.dumps(obj.revoke_map,
                                  registry=self._registry)

    def deserialize(self, data):
        revoke_map = msgpackutils.loads(data, registry=self._registry)
        revoke_tree = revoke_model.RevokeTree()
        revoke_tree.revoke_map = revoke_map
        return revoke_tree


# Register our new handler.
_registry = msgpackutils.default_registry
_registry.frozen = False
_registry.register(_RevokeModelHandler(registry=_registry))
_registry.frozen = True


class _ResponseCacheProxy(proxy.ProxyBackend):

    __key_pfx = '_request_cache_%s'

    def _get_request_context(self):
        return oslo_context.get_current() or oslo_context.RequestContext()

    def _get_request_key(self, key):
        return self.__key_pfx % key

    def get(self, key):
        ctx = self._get_request_context()
        try:
            value = getattr(ctx, self._get_request_key(key))
            value = msgpackutils.loads(value)
            return api.CachedValue(payload=value['payload'],
                                   metadata=value['metadata'])
        except AttributeError:
            return self.proxied.get(key)

    def set(self, key, value):
        ctx = self._get_request_context()
        self.proxied.set(key, value)
        serialize = {'payload': value.payload, 'metadata': value.metadata}
        setattr(ctx, self._get_request_key(key), msgpackutils.dumps(serialize))
        ctx.update_store()

    def delete(self, key):
        ctx = self._get_request_context()
        try:
            delattr(ctx, self._get_request_key(key))
            ctx.update_store()
        except AttributeError:  # nosec
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
