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

from keystone import assignment
from keystone import auth
from keystone import catalog
from keystone.common import cache
from keystone.common import dependency
from keystone.contrib import endpoint_filter
from keystone.contrib import federation
from keystone.contrib import oauth1
from keystone.contrib import revoke
from keystone import credential
from keystone import endpoint_policy
from keystone import identity
from keystone import policy
from keystone import resource
from keystone import token
from keystone import trust


def load_backends():

    # Configure and build the cache
    cache.configure_cache_region(cache.REGION)

    # Ensure that the identity driver is created before the assignment manager
    # and that the assignment driver is created before the resource manager.
    # The default resource driver depends on assignment, which in turn
    # depends on identity - hence we need to ensure the chain is available.
    identity_api = identity.Manager()
    dependency.set_provider('identity_api', identity_api)
    assignment_api = assignment.Manager()
    dependency.set_provider('assignment_api', assignment_api)

    catalog_api = catalog.Manager()
    dependency.set_provider('catalog_api', catalog_api)

    credential_api = credential.Manager()
    dependency.set_provider('credential_api', credential_api)

    domain_config_api = resource.DomainConfigManager()
    dependency.set_provider('domain_config_api', domain_config_api)

    endpoint_filter_api = endpoint_filter.Manager()
    dependency.set_provider('endpoint_filter_api', endpoint_filter_api)

    endpoint_policy_api = endpoint_policy.Manager()
    dependency.set_provider('endpoint_policy_api', endpoint_policy_api)

    federation_api = federation.Manager()
    dependency.set_provider('federation_api', federation_api)

    id_generator_api = identity.generator.Manager()
    dependency.set_provider('id_generator_api', id_generator_api)

    id_mapping_api = identity.MappingManager()
    dependency.set_provider('id_mapping_api', id_mapping_api)

    oauth_api = oauth1.Manager()
    dependency.set_provider('oauth_api', oauth_api)

    policy_api = policy.Manager()
    dependency.set_provider('policy_api', policy_api)

    resource_api = resource.Manager()
    dependency.set_provider('resource_api', resource_api)

    revoke_api = revoke.Manager()
    dependency.set_provider('revoke_api', revoke_api)

    role_api = assignment.RoleManager()
    dependency.set_provider('role_api', role_api)

    token_api = token.persistence.Manager()
    dependency.set_provider('token_api', token_api)

    token_provider_api = token.provider.Manager()
    dependency.set_provider('token_provider_api', token_provider_api)

    trust_api = trust.Manager()
    dependency.set_provider('trust_api', trust_api)

    DRIVERS = dict(
        assignment_api=assignment_api,
        catalog_api=catalog_api,
        credential_api=credential_api,
        domain_config_api=domain_config_api,
        endpoint_filter_api=endpoint_filter_api,
        endpoint_policy_api=endpoint_policy_api,
        federation_api=federation_api,
        id_generator_api=id_generator_api,
        id_mapping_api=id_mapping_api,
        identity_api=identity_api,
        oauth_api=oauth_api,
        policy_api=policy_api,
        resource_api=resource_api,
        revoke_api=revoke_api,
        role_api=role_api,
        token_api=token_api,
        trust_api=trust_api,
        token_provider_api=token_provider_api)

    auth.controllers.load_auth_methods()

    return DRIVERS
