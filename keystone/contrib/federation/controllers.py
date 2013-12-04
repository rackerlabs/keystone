# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

"""Extensions supporting Federation."""

from keystone.common import controller
from keystone.common import dependency
from keystone import config
from keystone import exception

CONF = config.CONF


@dependency.requires('federation_api')
class IdentityProvider(controller.V3Controller):
    collection_name = 'identity_providers'
    member_name = 'identity_provider'

    _mutable_parameters = frozenset(['description', 'name',
                                     'enabled'])
    _public_parameters = frozenset(['id', 'name',
                                    'enabled', 'domain_id',
                                    'description', 'public_keys',
                                    'protocols', 'links'])

    @classmethod
    def check_immutable_params(cls, ref, keys=None):
        """Raise exception when unallowed parameter is stored in the keys

        Unless the keys argument is specified, use the class list.
        @raises exception.ImmutableAttributeError
        """
        if keys is None:
            keys = cls._mutable_parameters

        ref_keys = set(ref.keys())
        blocked_keys = ref_keys - keys
        for blocked_param in blocked_keys:
            exception_args = {'target': cls.__name__,
                              'attribute': blocked_param}
            raise exception.ImmutableAttributeError(**exception_args)

    @classmethod
    def filter_params(cls, ref, keys=None):
        """Remove unspecified parameters from the dictionary.

        Unless the keys argument is specified, use the class list
        This function will remove unspecified parameters from the dictionary.
        See check_immutable_parameters for corresponding function that raises
        exceptions.
        """
        if keys is None:
            keys = cls._public_parameters
        ref_keys = set(ref.keys())
        blocked_keys = ref_keys - keys
        for blocked_param in blocked_keys:
            del ref[blocked_param]
        return ref

    @classmethod
    def base_url(cls, path=None):
        path = '/OS-IDP/' + cls.collection_name
        return controller.V3Controller.base_url(path=path)

    def _delete_tokens_issued_by_idp(self, idp_id):
        pass

    @controller.protected()
    def create_federated_provider(self, context, identity_provider):
        allowed_params = set(['id', 'name', 'description', 'enabled',
                              'domain_id'])

        ref = self._assign_unique_id(self._normalize_dict(identity_provider))

        IdentityProvider.check_immutable_params(ref, keys=allowed_params)
        idp_ref = self.federation_api.create_idp(ref)
        idp_ref = IdentityProvider.filter_params(idp_ref, keys=allowed_params)
        return IdentityProvider.wrap_member(context, idp_ref)

    @controller.protected()
    def list_federated_providers(self, context):
        ref = self.federation_api.list_idps()
        ref = [self.filter_params(x) for x in ref]
        return IdentityProvider.wrap_collection(context, ref)

    @controller.protected()
    def get_federated_provider(self, context, idp_id):
        ref = self.federation_api.get_idp(idp_id)
        ref = self.filter_params(ref)
        return IdentityProvider.wrap_member(context, ref)

    @controller.protected()
    def delete_federated_provider(self, context, idp_id):
        self.federation_api.delete_idp(idp_id)
        self._delete_tokens_issued_by_idp(idp_id)

    @controller.protected()
    def update_federated_provider(self, context, idp_id, identity_provider):
        identity_provider = self._normalize_dict(identity_provider)
        IdentityProvider.check_immutable_params(identity_provider)
        idp_ref = self.federation_api.update_idp(idp_id, identity_provider)
        return IdentityProvider.wrap_member(context, idp_ref)


@dependency.requires('federation_api')
class ProviderPublicKey(IdentityProvider):
    collection_name = 'public_keys'
    member_name = 'public_key'

    _public_parameters = frozenset(['id', 'key', 'links'])
    _mutable_parameters = frozenset(['key'])

    @classmethod
    def wrap_member(cls, context, ref):
        cls._add_self_referential_link(ref)
        ref = cls.filter_params(ref)
        return {cls.member_name: ref}

    @classmethod
    def _add_self_referential_link(cls, ref):
        id = ref['id']
        idp_id = ref['idp_id']
        path = (IdentityProvider.base_url(), idp_id,
                cls.collection_name, id)
        path = '/'.join(path)
        ref.setdefault('links', {})
        ref['links']['self'] = path

    @controller.protected()
    def get_provider_key(self, context, idp_id, key_id):
        key_ref = self.federation_api.get_idp_key(idp_id, key_id)
        return ProviderPublicKey.wrap_member(context, key_ref)

    @controller.protected()
    def put_provider_key(self, context, idp_id, public_key):
        ref = self._normalize_dict(public_key)
        ProviderPublicKey.check_immutable_params(ref)
        ref = self._assign_unique_id(ref)
        key_ref = self.federation_api.put_idp_key(idp_id, ref)
        return ProviderPublicKey.wrap_member(context, key_ref)

    @controller.protected()
    def update_provider_key(self, context, idp_id, key_id, public_key):
        ref = self._normalize_dict(public_key)
        ProviderPublicKey.check_immutable_params(ref)
        ref = self.federation_api.update_idp_key(idp_id, key_id, public_key)
        return ProviderPublicKey.wrap_member(context, ref)

    @controller.protected()
    def list_provider_keys(self, context, idp_id):
        key_ref = self.federation_api.list_public_keys(idp_id)
        return ProviderPublicKey.wrap_collection(context, key_ref)

    @controller.protected()
    def delete_provider_key(self, context, idp_id, key_id):
        self.federation_api.delete_idp_key(idp_id, key_id)


@dependency.requires('federation_api')
class FederationProtocol(IdentityProvider):
    collection_name = 'protocols'
    member_name = 'protocol'

    _public_parameters = frozenset(['id', 'name', 'mapping_id', 'links'])
    _mutable_parameters = set(['mapping_id'])

    @classmethod
    def wrap_member(cls, context, ref):
        cls._add_self_referential_link(ref)
        ref = cls.filter_params(ref)
        return {cls.member_name: ref}

    @classmethod
    def _add_self_referential_link(cls, ref):
        id = ref['id']
        idp_id = ref['idp_id']
        path = (IdentityProvider.base_url(), idp_id,
                cls.collection_name, id)
        path = '/'.join(path)
        ref.setdefault('links', {})
        ref['links']['self'] = path

    @controller.protected()
    def put_protocol(self, context, idp_id, protocol):
        ref = self._normalize_dict(protocol)
        keys = self._mutable_parameters.copy()
        keys.update(['id'])
        FederationProtocol.check_immutable_params(ref, keys=keys)
        ref = self.federation_api.put_protocol(idp_id, ref)
        return FederationProtocol.wrap_member(context, ref)

    @controller.protected()
    def update_protocol(self, context, idp_id, protocol_id, protocol):
        ref = self._normalize_dict(protocol)
        FederationProtocol.check_immutable_params(ref)
        ref = self.federation_api.update_protocol(idp_id, protocol_id,
                                                  protocol)
        return FederationProtocol.wrap_member(context, ref)

    @controller.protected()
    def get_protocol(self, context, idp_id, protocol_id):
        ref = self.federation_api.get_protocol(idp_id, protocol_id)
        return FederationProtocol.wrap_member(context, ref)

    @controller.protected()
    def list_protocols(self, context, idp_id):
        protocols_ref = self.federation_api.list_protocols(idp_id)
        protocols = list(protocols_ref)
        return FederationProtocol.wrap_collection(context, protocols)

    @controller.protected()
    def delete_protocol(self, context, idp_id, protocol_id):
        self.federation_api.delete_protocol(idp_id, protocol_id)
