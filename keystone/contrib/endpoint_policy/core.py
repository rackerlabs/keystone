# Copyright 2014 IBM Corp.
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

import abc

import six

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import config
from keystone import exception


CONF = config.CONF

extension_data = {
    'name': 'OpenStack Keystone Endpoint Policy API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-ENDPOINT-POLICY/v1.0',
    'alias': 'OS-ENDPOINT-POLICY',
    'updated': '2014-08-18T12:00:0-00:00',
    'description': 'OpenStack Keystone Endpoint Policy API.',
    'links': [
        {
            'rel': 'describedby',
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api/blob/master'
                    '/openstack-identity-api/v3/src/markdown/'
                    'identity-api-v3-os-endpoint-policy-ext.md',
        }
    ]}
extension.register_admin_extension(extension_data['alias'], extension_data)


@dependency.provider('endpoint_policy_api')
class Manager(manager.Manager):
    """Default pivot point for the Endpoint Policy backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.endpoint_policy.driver)


@six.add_metaclass(abc.ABCMeta)
class Driver(object):
    """Interface description for an Endpoint Policy driver."""

    @abc.abstractmethod
    def create_policy_association(self, policy_id, endpoint_id=None,
                                  service_id=None, region_id=None):
        """Creates a policy association.

        :param policy: identity of policy that is being associated
        :type policy: string
        :param endpoint_id: identity of endpoint to associate
        :type endpoint_id: string
        :param service_id: identity of the service to associate
        :type service_id: string
        :param region_id: identity of the region to associate
        :type region_id: string
        :raises: keystone.exception.InvalidPolicyAssociation
        :returns: None

        There are three types of association permitted:

        - Endpoint (in which case service and region must be None)
        - Service and region (in which endpoint must be None)
        - Service (in which case endpoint and region must be None)

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def check_policy_association(self, policy_id, endpoint_id=None,
                                 service_id=None, region_id=None):
        """Checks existence a policy association.

        :param policy: identity of policy that is being associated
        :type policy: string
        :param endpoint_id: identity of endpoint to associate
        :type endpoint_id: string
        :param service_id: identity of the service to associate
        :type service_id: string
        :param region_id: identity of the region to associate
        :type region_id: string
        :raises: keystone.exception.InvalidPolicyAssociation
        :returns: None

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_policy_association(self, policy_id, endpoint_id=None,
                                  service_id=None, region_id=None):
        """Deletes a policy association.

        :param policy: identity of policy that is being associated
        :type policy: string
        :param endpoint_id: identity of endpoint to associate
        :type endpoint_id: string
        :param service_id: identity of the service to associate
        :type service_id: string
        :param region_id: identity of the region to associate
        :type region_id: string
        :raises: keystone.exception.InvalidPolicyAssociation
        :returns: None

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_endpoints_for_policy(self, policy_id):
        """List all the endpoints using a given policy.

        :param policy: identity of policy that is being associated
        :type policy: string
        :returns: list of endpoints that have an effective association with
                  that policy

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_policy_for_endpoint(self, endpoint_id):
        """Get the appropriate policy for a given endpoint.

        :param endpoint_id: identity of endpoint
        :type endpoint_id: string
        :returns: Policy entity for the endpoint


        """
        raise exception.NotImplemented()  # pragma: no cover
