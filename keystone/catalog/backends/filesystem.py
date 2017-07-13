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
          -
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
                # NOTE: The above endpoint will not render in the v2 catalog.
            region: RegionOne
            service: ServiceOne
            id: EndpointOne
          -
            interfaces:
              -
                type: public
                url: "https://compute.example.com/v2.1/"
            region: RegionOne
            service: ServiceTwo
            id: EndpointTwo

          -
            interfaces:
              -
                type: public
                url: "https://volume.example.com/v2/{project_id}"
            region: RegionOne
            service: ServiceThree
            id: EndpointThree
        regions:
          RegionOne:
            description: "First Region"
          RegionTwo:
            description: "Second Region"
            parent_region: RegionOne
        services:
          ServiceOne:
            type: identity
          ServiceThree:
            type: volume
          ServiceTwo:
            type: compute
    """

    def __init__(self):
        super(Catalog, self).__init__()
        yaml_file = CONF.catalog.filesystem_yaml_file
        if not os.path.exists(yaml_file):
            yaml_file = CONF.find_file(yaml_file)
        try:
            with open(yaml_file) as f:
                self.__catalog_data = yaml.safe_load(f)
        except IOError:
            LOG.critical('Unable to open yaml file %s', yaml_file)
            raise
        self._validate_catalog_data()

    def _validate_catalog_data(self):
        # TODO(morgan): verify the loaded data makes sense.
        pass

    def _build_region_data(self, region_id, region_dict_from_conf):
        valid_keys = ('description', 'parent_region_id')
        r_data = {'id': region_id}
        # Ensure we are working with a dict instead of a None.
        # Regions need to be dicts loaded from the yaml
        for k in valid_keys:
            if k in region_dict_from_conf:
                r_data[k] = region_dict_from_conf[k]
        return r_data

    def list_regions(self, hints):
        c_data_regions = self.__catalog_data.get('regions', {})
        return [self._build_region_data(rid, c_data_regions.get(rid, {}))
                for rid in c_data_regions.keys()]

    def get_region(self, region_id):
        c_data_regions = self.__catalog_data.get('regions', {})
        if region_id in c_data_regions:
            return self._build_region_data(
                region_id, (c_data_regions.get(region_id) or {}))
        raise exception.RegionNotFound(region_id=region_id)

    def _build_endpoint_data(self, endpoint_id, endpoint_dict_from_conf):
        optional_keys = ('region_id',)
        e_data = {'id': endpoint_id}
        try:
            sid = endpoint_dict_from_conf['service_id']
            self.get_service(sid)
            e_data['service_id'] = sid
        except (KeyError, exception.ServiceNotFound):
                raise ValueError(_('endpoint must have a valid service_id'))

        for req in ('url', 'interface'):
            msg = _('endpoint must have a valid value for `%s`')
            try:
                e_data[req] = endpoint_dict_from_conf[req]
            except KeyError:
                raise ValueError(msg % req)
            else:
                if not e_data[req]:
                    raise ValueError(msg % req)

        for op_k in optional_keys:
            if op_k in endpoint_dict_from_conf:
                e_data[op_k] = endpoint_dict_from_conf[op_k]
        return e_data

    def list_endpoints(self, hints):
        c_data_endpoints = self.__catalog_data.get('endpoints', {})
        return [self._build_endpoint_data(e, c_data_endpoints.get(e) or {})
                for e in c_data_endpoints.keys()]

    def get_endpoint(self, endpoint_id):
        c_data_endpoints = self.__catalog_data.get('endpoints', {})
        if endpoint_id in c_data_endpoints:
            return self._build_endpoint_data(
                endpoint_id, c_data_endpoints.get(endpoint_id, {}) or {})

    def _build_service_data(self, service_id, service_dict_from_conf):
        valid_keys = ('type', )
        s_data = {'id': service_id}
        for k in valid_keys:
            if k in service_dict_from_conf:
                s_data[k] = service_dict_from_conf[k]
        return s_data

    def list_services(self, hints):
        c_data_services = self.__catalog_data.get('services', {})
        return [self._build_service_data(s, c_data_services.get(s, {}))
                for s in c_data_services.keys()]

    def get_service(self, service_id):
        c_data_services = self.__catalog_data.get('services', {})
        if service_id in c_data_services:
            return self._build_service_data(
                service_id, c_data_services.get(service_id, {}))
        raise exception.ServiceNotFound(service_id=service_id)

    def get_catalog(self, user_id, project_id):
        """Retrieve and format the V2 service catalog.

        :param user_id: The id of the user who has been authenticated for
            creating service catalog.
        :param project_id: The id of the project. 'project_id' will be None in
            the case this being called to create a catalog to go in a domain
            scoped token. In this case, any endpoint that requires a project_id
            as part of their URL will be skipped.

        :returns: A nested dict representing the service catalog or an
                  empty dict.

        """
        substitutions = dict(
            itertools.chain(CONF.items(), CONF.eventlet_server.items()))
        substitutions.update({'user_id': user_id})
        valid_interface_types = ('admin', 'public', 'internal')
        silent_keyerror_failures = []
        if project_id:
            substitutions.update(
                {'tenant_id': project_id, 'project_id': project_id})
        else:
            silent_keyerror_failures = ['tenant_id', 'project_id']

        catalog = {}
        for endpoint in (self.__catalog_data.get('endpoints') or []):
            region = endpoint.get('region')

            try:
                # check to see if service / region exist
                service = self.get_service(endpoint.get('service'))
                if region:
                    self.get_region(region)
            except (exception.ServiceNotFound, exception.RegionNotFound) as e:
                # If there is a service not found, or a region is specified
                # for the endpoint and it doesn't exist, the endpoint is
                # considered invalid and will not rendered in the catalog.
                # This is intentionally silent.
                if isinstance(e, exception.ServiceNotFound):
                    missing = 'service'
                    invalid = endpoint['service']
                else:
                    missing = 'region'
                    invalid = endpoint['region']

                LOG.warning('Endpoint `%(endpoint)r` has an invalid (not '
                            'found) %(service)s defined: `%(invalid)s`. It '
                            'will not be rendered in the catalog.',
                            dict(endpoint=endpoint, service=missing,
                                 invalid=invalid))
                continue

            for interface_type in valid_interface_types:
                url = None

                for i in endpoint['interfaces']:
                    if i['type'] == interface_type:
                        url = i.get('url')
                        break

                if url is None:
                    # This URL doesn't actually exist, do not add it to the
                    # catalog
                    continue
                try:
                    formatted_url = utils.format_url(
                        url, substitutions,
                        silent_keyerror_failures=silent_keyerror_failures)
                    if formatted_url is None:
                        continue
                except exception.MalformedEndpoint:  # nosec
                    continue  # this failure is already logged in format_url()

                catalog.setdefault(region, {})
                url_type = '%sURL' % interface_type
                service_type = service['type']
                ep_rendered = {'id': endpoint['id'],
                               'name': endpoint['id'],
                               url_type: formatted_url}
                catalog[region].setdefault(service_type, ep_rendered)
        return catalog

    def get_v3_catalog(self, user_id, project_id):
        """Retrieve and format the current V3 service catalog.

        The default implementation builds the V3 catalog from the V2 catalog.

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
                    }],
                "id": "--service-id--",
                "type": "volume"
            }]

        :returns: A list representing the service catalog or an empty list
        :raises keystone.exception.NotFound: If the endpoint doesn't exist.

        """
        substitutions = dict(
            itertools.chain(CONF.items(), CONF.eventlet_server.items()))
        substitutions.update({'user_id': user_id})
        silent_keyerror_failures = []
        if project_id:
            substitutions.update(
                {'tenant_id': project_id, 'project_id': project_id})
        else:
            silent_keyerror_failures = ['tenant_id', 'project_id']

        catalog = []
        services_rendered = {}
        for endpoint in (self.__catalog_data.get('endpoints') or []):
            region = endpoint.get('region')

            try:
                # check to see if service / region exist
                service_id = endpoint.get('service')
                service = self.get_service(service_id)
                if region:
                    self.get_region(region)
            except (exception.ServiceNotFound, exception.RegionNotFound) as e:
                # If there is a service not found, or a region is specified
                # for the endpoint and it doesn't exist, the endpoint is
                # considered invalid and will not rendered in the catalog.
                # This is intentionally silent.
                if isinstance(e, exception.ServiceNotFound):
                    missing = 'service'
                    invalid = endpoint['service']
                else:
                    missing = 'region'
                    invalid = endpoint['region']

                LOG.warning('Endpoint `%(endpoint)r` has an invalid (not '
                            'found) %(service)s defined: `%(invalid)s`. It '
                            'will not be rendered in the catalog.',
                            dict(endpoint=endpoint, service=missing,
                                 invalid=invalid))
                continue

            for interface in endpoint.get('interfaces', []):
                url = interface.get('url')
                i_type = interface.get('type')
                if url is None:
                    # This URL doesn't actually exist, do not add it to the
                    # catalog
                    continue
                try:
                    formatted_url = utils.format_url(
                        url, substitutions,
                        silent_keyerror_failures=silent_keyerror_failures)
                    if formatted_url is None:
                        continue
                except exception.MalformedEndpoint:  # nosec
                    continue  # this failure is already logged in format_url()
                ep_id = uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    '%(id)s-%(interface)s' % {'id': endpoint['id'],
                                              'interface': i_type})
                s_rendered = services_rendered.get(service_id)
                if service_id is None:
                    s_rendered = services_rendered.setdefault(
                        service_id, {'id': service_id,
                                     'type': service['type']})
                    catalog.append(s_rendered)
                ep_rendered = {'id': ep_id,
                               'interface': i_type,
                               'url': formatted_url}
                if region:
                    ep_rendered['region'] = region
                s_rendered.setdefault('endpoints', []).append(ep_rendered)
        return catalog

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
