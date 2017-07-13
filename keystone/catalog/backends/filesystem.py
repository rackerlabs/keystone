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

import itertools
import os
import uuid

from oslo_log import log
import yaml

from keystone.catalog.backends import base
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone.i18n import _


LOG = log.getLogger(__name__)

CONF = keystone.conf.CONF


class Catalog(base.CatalogDriverBase):
    """A backend that generates catalogs from data in a yaml file on disk.

    Each type of resource for the catalog is specified in the yaml, there is
    validation to make sure all the information needed to create a valid
    catalog is supplied. You may reference data in the yaml standard way(s) or
    duplicate the elements. Valid substitutions are ``{project_id}``,
    ``{admin_port}``, ``{public_port}``. Example(s)::

        ---
        endpoints:
          EndpointOne:
            interfaces:
              -
                type: public
                url: "https://identity.example.com"
              -
                type: internal
                url: "https://internal-indentity.example.com"
              -
                type: admin
                url: "https://admin-identity.example.com"
              -
                type: other
                url: "https://something-else-identity.example.com"
            region: RegionOne
            service: ServiceOne
          EndpointTwo:
            interfaces:
              -
                type: public
                url: "https://compute.example.com/v2.1/"
            region: RegionOne
            service: ServiceTwo
          EndpointThree:
            interfaces:
              -
                type: public
                url: "https://volume.example.com/v2/$(project_id)s"
            region: RegionOne
            service: ServiceThree
        regions:
          RegionOne:
            description: "First Region"
          RegionTwo:
            description: "Second Region"
            parent_region_id: RegionOne
        services:
          ServiceOne:
            type: identity
            name: keystone
          ServiceThree:
            type: volume
          ServiceTwo:
            type: compute
    """

    def __init__(self):
        super(Catalog, self).__init__()
        self.__catalog_data = {}
        self.yaml_file = CONF.catalog.catalog_file
        if not os.path.exists(self.yaml_file):
            self.yaml_file = CONF.find_file(self.yaml_file)
        try:
            with open(self.yaml_file) as f:
                self.__catalog_data['mtime'] = os.path.getmtime(self.yaml_file)
                self._build_and_validate_catalog_data(yaml.safe_load(f))

        except IOError:
            LOG.critical('Failed to load catalog data from %(file)s. '
                         'Please make sure the file exists and keystone '
                         'has access to read it.', self.yaml_file)
            raise

    def _build_and_validate_catalog_data(self, data):
        self.__catalog_data['regions'] = self._build_region_data(
            data.get('regions', {}))
        self.__catalog_data['services'] = self._build_service_data(
            data.get('services', {}))
        self.__catalog_data['endpoints'] = []

        for eid, endpoint in (data.get('endpoints', {})).items():
            region_id = endpoint.get('region')
            try:
                service_id = endpoint['service']
                self.get_service(service_id)
                if region_id is not None:
                    self.get_region(region_id)
            except KeyError:
                raise ValueError(_(
                    'Endpoint `%(endpoint_id)s` must have a service defined') %
                    {'endpoint_id': eid})
            except exception.ServiceNotFound:
                raise ValueError(_(
                    'Endpoint `%(endpoint_id)s` has an invalid (not found) '
                    'service defined: `%(service_id)`') %
                    {'endpoint_id': eid, 'service': service_id})
            except exception.RegionNotFound:
                raise ValueError(_(
                    'Endpoint `%(endpoint_id)s` has an invalid (not found) '
                    'region defined: `%(region_id)s`') %
                    {'endpoint_id': eid, 'region_id': region_id})

            for interface in endpoint.get('interfaces', []):
                if 'type' not in interface or 'url' not in interface:
                    raise ValueError(_('Endpoint `%{endpoint_id}` is missing'
                                       'either "type" or "url" in interface'
                                       'definition: `%(iface)r`.') %
                                     {'endpoint_id': eid, 'iface': interface})
                v3_endpoint = {
                    'id': uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        '%(id)s-%(type)s' % {'id': eid,
                                             'type': interface['type']}).hex,
                    'interface': interface['type'],
                    'url': interface['url'],
                    'service_id': service_id,
                    'legacy_endpoint_id': eid,
                    'enabled': True}
                if region_id is not None:
                    v3_endpoint['region_id'] = region_id
                self.__catalog_data['endpoints'].append(v3_endpoint)

    def _build_region_data(self, data):
        regions = {}
        for rid, region in data.items():
            r_data = {'id': rid,
                      'description': '',
                      'parent_region_id': None}
            if region is not None:
                r_data['description'] = region.get('description', '')
                r_data['parent_region_id'] = region.get('parent_region_id')
            regions[rid] = r_data
        return regions

    def _build_service_data(self, data):
        services = {}
        for sid, service in data.items():
            valid_keys = ('description',)
            s_data = {'id': sid, 'name': sid, 'enabled': True}
            try:
                s_data['type'] = service['type']
            except (KeyError, TypeError):
                raise ValueError(_(
                    'Service `%(service_id)s` must have a type.') %
                    {'service_id': sid})
            for k in valid_keys:
                if k in service:
                    s_data[k] = service[k]
            services[sid] = s_data
        return services

    def _refresh_catalog_if_needed(self):
        mtime = os.path.getmtime(self.yaml_file)
        if mtime > self.__catalog_data.get('mtime', 0):
            LOG.debug("Reloading cached file %s", self.yaml_file)
            with open(self.yaml_file) as file:
                self.__catalog_data.clear()
                self.__catalog_data['mtime'] = mtime
                self._build_and_validate_catalog_data(yaml.safe_load(file))

    def list_regions(self, hints):
        self._refresh_catalog_if_needed()
        return [region for _, region in self.__catalog_data['regions'].items()]

    def get_region(self, region_id):
        self._refresh_catalog_if_needed()
        try:
            return self.__catalog_data['regions'][region_id]
        except KeyError:
            raise exception.RegionNotFound(region_id=region_id)

    def list_endpoints(self, hints):
        self._refresh_catalog_if_needed()
        return self.__catalog_data['endpoints']

    def get_endpoint(self, endpoint_id):
        self._refresh_catalog_if_needed()
        for endpoint in self.__catalog_data['endpoints']:
            if endpoint['id'] == endpoint_id:
                return endpoint
        raise exception.EndpointNotFound(endpoint_id=endpoint_id)

    def list_services(self, hints):
        self._refresh_catalog_if_needed()
        return [service for _, service in
                self.__catalog_data['services'].items()]

    def get_service(self, service_id):
        self._refresh_catalog_if_needed()
        try:
            return self.__catalog_data['services'][service_id]
        except KeyError:
            raise exception.ServiceNotFound(service_id=service_id)

    def get_v3_catalog(self, user_id, project_id):
        """Retrieve and format the current V3 service catalog.

        Example::

            [
                {
                    "endpoints": [
                        {
                            "interface": "public",
                            "id": "--endpoint-id--",
                            "region": "RegionOne",
                            "url": "http://external:8776/v1/--project-id--"
                        },
                        {
                            "interface": "internal",
                            "id": "--endpoint-id--",
                            "region": "RegionOne",
                            "url": "http://internal:8776/v1/--project-id--"
                        }
                    ],
                    "id": "--service-id--",
                    "type": "volume"
                    "name": "ServiceOne"
                }
            ]

        :returns: A list representing the service catalog or an empty list
        :raises keystone.exception.NotFound: If the endpoint doesn't exist.

        """
        self._refresh_catalog_if_needed()
        substitutions = dict(
            itertools.chain(CONF.items(), CONF.eventlet_server.items()))
        substitutions.update({'user_id': user_id})
        silent_keyerror_failures = []
        if project_id:
            substitutions.update({'project_id': project_id})
        else:
            silent_keyerror_failures = ['project_id']

        catalog = []
        services_rendered = {}
        for endpoint in (self.__catalog_data.get('endpoints', [])):

            ep_rendered = {'interface': endpoint['interface'],
                           'id': endpoint['id'],
                           'region': endpoint['region_id']}
            try:
                formatted_url = utils.format_url(
                    endpoint['url'], substitutions,
                    silent_keyerror_failures=silent_keyerror_failures)
                if formatted_url is None:
                    continue
            except exception.MalformedEndpoint:  # nosec
                continue  # this failure is already logged in format_url()
            ep_rendered['url'] = formatted_url

            sid = endpoint['service_id']
            if sid not in services_rendered:
                stype = self.__catalog_data.get('services')[sid].get('type')
                sname = self.__catalog_data.get('services')[sid].get('name')
                s_rendered = services_rendered.setdefault(
                    sid, {'id': sid, 'type': stype, 'name': sname,
                          'endpoints': []})
                catalog.append(s_rendered)
            else:
                s_rendered = services_rendered[sid]

            s_rendered['endpoints'].append(ep_rendered)

        return catalog

    def get_catalog(self, user_id, project_id):
        # NOTE: filesystem catalog backend doesn't work for V2 APIs.
        raise exception.NotImplemented()

    # NOTE(notmorgan): this driver is read-only, all methods below this point
    # are not implemented as they are tied to write-operations in one form
    # or another.
    def create_region(self, region_ref):
        raise exception.NotImplemented()

    def update_region(self, region_id, region_ref):
        raise exception.NotImplemented()

    def delete_region(self, region_id):
        raise exception.NotImplemented()

    def create_service(self, service_id, service_ref):
        raise exception.NotImplemented()

    def update_service(self, service_id, service_ref):
        raise exception.NotImplemented()

    def delete_service(self, service_id):
        raise exception.NotImplemented()

    def create_endpoint(self, endpoint_id, endpoint_ref):
        raise exception.NotImplemented()

    def update_endpoint(self, endpoint_id, endpoint_ref):
        raise exception.NotImplemented()

    def delete_endpoint(self, endpoint_id):
        raise exception.NotImplemented()

    def add_endpoint_to_project(self, endpoint_id, project_id):
        raise exception.NotImplemented()

    def remove_endpoint_from_project(self, endpoint_id, project_id):
        raise exception.NotImplemented()

    def check_endpoint_in_project(self, endpoint_id, project_id):
        raise exception.NotImplemented()

    def list_endpoints_for_project(self, project_id):
        raise exception.NotImplemented()

    def list_projects_for_endpoint(self, endpoint_id):
        raise exception.NotImplemented()

    def delete_association_by_endpoint(self, endpoint_id):
        raise exception.NotImplemented()

    def delete_association_by_project(self, project_id):
        raise exception.NotImplemented()

    def create_endpoint_group(self, endpoint_group):
        raise exception.NotImplemented()

    def get_endpoint_group(self, endpoint_group_id):
        raise exception.NotImplemented()

    def update_endpoint_group(self, endpoint_group_id, endpoint_group):
        raise exception.NotImplemented()

    def delete_endpoint_group(self, endpoint_group_id):
        raise exception.NotImplemented()

    def add_endpoint_group_to_project(self, endpoint_group_id, project_id):
        raise exception.NotImplemented()

    def get_endpoint_group_in_project(self, endpoint_group_id, project_id):
        raise exception.NotImplemented()

    def list_endpoint_groups(self):
        raise exception.NotImplemented()

    def list_endpoint_groups_for_project(self, project_id):
        raise exception.NotImplemented()

    def list_projects_associated_with_endpoint_group(self, endpoint_group_id):
        raise exception.NotImplemented()

    def remove_endpoint_group_from_project(self, endpoint_group_id,
                                           project_id):
        raise exception.NotImplemented()

    def delete_endpoint_group_association_by_project(self, project_id):
        raise exception.NotImplemented()
