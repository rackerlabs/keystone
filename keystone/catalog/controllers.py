# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
# Copyright 2012 Canonical Ltd.
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

import uuid

from keystone.catalog import core
from keystone.common import controller
from keystone.common import wsgi
from keystone import exception
from keystone import identity
from keystone import policy
from keystone import token


class Service(wsgi.Application):
    def __init__(self):
        self.catalog_api = core.Manager()
        self.identity_api = identity.Manager()
        self.policy_api = policy.Manager()
        self.token_api = token.Manager()
        super(Service, self).__init__()

    def get_services(self, context):
        self.assert_admin(context)
        service_list = self.catalog_api.list_services(context)
        return {'OS-KSADM:services': service_list}

    def get_service(self, context, service_id):
        self.assert_admin(context)
        service_ref = self.catalog_api.get_service(context, service_id)
        return {'OS-KSADM:service': service_ref}

    def delete_service(self, context, service_id):
        self.assert_admin(context)
        self.catalog_api.delete_service(context, service_id)

    def create_service(self, context, OS_KSADM_service):
        self.assert_admin(context)
        service_id = uuid.uuid4().hex
        service_ref = OS_KSADM_service.copy()
        service_ref['id'] = service_id
        new_service_ref = self.catalog_api.create_service(
            context, service_id, service_ref)
        return {'OS-KSADM:service': new_service_ref}


class Endpoint(wsgi.Application):
    def __init__(self):
        self.catalog_api = core.Manager()
        self.identity_api = identity.Manager()
        self.policy_api = policy.Manager()
        self.token_api = token.Manager()
        super(Endpoint, self).__init__()

    def get_endpoints(self, context):
        self.assert_admin(context)
        endpoint_list = self.catalog_api.list_endpoints(context)
        return {'endpoints': endpoint_list}

    def create_endpoint(self, context, endpoint):
        self.assert_admin(context)
        endpoint_id = uuid.uuid4().hex
        endpoint_ref = endpoint.copy()
        endpoint_ref['id'] = endpoint_id
        new_endpoint_ref = self.catalog_api.create_endpoint(
            context, endpoint_id, endpoint_ref)
        return {'endpoint': new_endpoint_ref}

    def delete_endpoint(self, context, endpoint_id):
        self.assert_admin(context)
        self.catalog_api.delete_endpoint(context, endpoint_id)


class ServiceV3(controller.V3Controller):

    def __init__(self):
        super(ServiceV3, self).__init__()

    @controller.protected
    def create_service(self, context, service):
        ref = self._assign_unique_id(self._normalize_dict(service))
        self._require_attribute(ref, 'type')

        ref = self.apis.catalog.create_service(context, ref['id'], ref)
        return {'service': ref}

    @controller.protected
    def list_services(self, context):
        refs = self.apis.catalog.list_services(context)
        refs = self._filter_by_attribute(context, refs, 'type')
        return {'services': self._paginate(context, refs)}

    @controller.protected
    def get_service(self, context, service_id):
        ref = self.apis.catalog.get_service(context, service_id)
        return {'service': ref}

    @controller.protected
    def update_service(self, context, service_id, service):
        self._require_matching_id(service_id, service)

        ref = self.apis.catalog.update_service(context, service_id, service)
        return {'service': ref}

    @controller.protected
    def delete_service(self, context, service_id):
        return self.apis.catalog.delete_service(context, service_id)


class EndpointV3(controller.V3Controller):

    def __init__(self):
        super(EndpointV3, self).__init__()

    @controller.protected
    def create_endpoint(self, context, endpoint):
        ref = self._assign_unique_id(self._normalize_dict(endpoint))
        self._require_attribute(ref, 'service_id')
        self._require_attribute(ref, 'interface')
        self.apis.catalog.get_service(context, ref['service_id'])

        ref = self.apis.catalog.create_endpoint(context, ref['id'], ref)
        return {'endpoint': ref}

    @controller.protected
    def list_endpoints(self, context):
        refs = self.apis.catalog.list_endpoints(context)
        refs = self._filter_by_attribute(context, refs, 'service_id')
        refs = self._filter_by_attribute(context, refs, 'interface')
        return {'endpoints': self._paginate(context, refs)}

    @controller.protected
    def get_endpoint(self, context, endpoint_id):
        ref = self.apis.catalog.get_endpoint(context, endpoint_id)
        return {'endpoint': ref}

    @controller.protected
    def update_endpoint(self, context, endpoint_id, endpoint):
        self._require_matching_id(endpoint_id, endpoint)

        if 'service_id' in endpoint:
            self.apis.catalog.get_service(context, endpoint['service_id'])

        ref = self.apis.catalog.update_endpoint(context, endpoint_id, endpoint)
        return {'endpoint': ref}

    @controller.protected
    def delete_endpoint(self, context, endpoint_id):
        return self.apis.catalog.delete_endpoint(context, endpoint_id)


class VersionController(wsgi.Application):
    def __init__(self, version_type):
        self.catalog_api = core.Manager()
        self.url_key = '%sURL' % version_type

        super(VersionController, self).__init__()

    def _get_identity_url(self, context):
        catalog_ref = self.catalog_api.get_catalog(context=context,
                                                   user_id=None,
                                                   tenant_id=None)
        for region, region_ref in catalog_ref.iteritems():
            for service, service_ref in region_ref.iteritems():
                if service == 'identity':
                    return service_ref[self.url_key]

        raise exception.NotImplemented()

    def _get_versions_list(self, context):
        """The list of versions is dependent on the context."""
        identity_url = self._get_identity_url(context)
        if not identity_url.endswith('/'):
            identity_url = identity_url + '/'

        versions = {}
        versions['v2.0'] = {
            'id': 'v2.0',
            'status': 'beta',
            'updated': '2011-11-19T00:00:00Z',
            'links': [
                {
                    'rel': 'self',
                    'href': identity_url,
                }, {
                    'rel': 'describedby',
                    'type': 'text/html',
                    'href': 'http://docs.openstack.org/api/openstack-'
                            'identity-service/2.0/content/'
                }, {
                    'rel': 'describedby',
                    'type': 'application/pdf',
                    'href': 'http://docs.openstack.org/api/openstack-'
                            'identity-service/2.0/identity-dev-guide-'
                            '2.0.pdf'
                }
            ],
            'media-types': [
                {
                    'base': 'application/json',
                    'type': 'application/vnd.openstack.identity-v2.0'
                            '+json'
                }, {
                    'base': 'application/xml',
                    'type': 'application/vnd.openstack.identity-v2.0'
                            '+xml'
                }
            ]
        }

        return versions

    def get_versions(self, context):
        versions = self._get_versions_list(context)
        return wsgi.render_response(status=(300, 'Multiple Choices'), body={
            'versions': {
                'values': versions.values()
            }
        })

    def get_version(self, context):
        versions = self._get_versions_list(context)
        return wsgi.render_response(body={
            'version': versions['v2.0']
        })
