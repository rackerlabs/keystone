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
                # NOTE: The "other" interface will not render in the v2 catalog
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
                url: "https://volume.example.com/v2/{project_id}"
            region: RegionOne
            service: ServiceThree
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
        self.__catalog_data = {}
        yaml_file = CONF.catalog.filesystem_yaml_file
        if not os.path.exists(yaml_file):
            yaml_file = CONF.find_file(yaml_file)
        try:
            with open(yaml_file) as f:
                self.build_and_verify_catalog_data(yaml.safe_load(f))
        except IOError:
            LOG.critical('Unable to open yaml file %s', yaml_file)
            raise
        self.build_and_validate_catalog_data()

    def _build_and_validate_catalog_data(self, data):
        self.__catalog_data['regions'] = self._build_region_data(
            data.get('regions', {}) or {})
        self.__catalog_data['services'] = self._build_service_data(
            data.get('services', {}) or {})
        self.__catalog_data['endpoints'] = {}
        catalog_eps = self.__catalog_data['endpoints']
        valid_v2_interface_types = ('admin', 'public', 'internal')

        for eid, endpoint in (data.get('endpooints', {}) or {}).items():
            region = endpoint.get('region')
            try:
                service_id = endpoint['service']
                service = self.get_service(service_id)
                if region is not None:
                    self.get_region(region)
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
                    {'endpoint_id': eid, 'region_id': region})

            v2_endpoint = {'id': eid, 'name': eid, 'version': 2}
            for iface in endpoint.get('interfaces', []) or []:
                if 'type' not in iface or 'url' not in iface:
                    raise ValueError(_('Endpoint `%{endpoint_id}` is missing'
                                       'either "type" or "url" in interface'
                                       'definition: `%(iface)r`.') %
                                     {'endpoint_id': eid, 'iface': iface})

                if iface['type'] in valid_v2_interface_types:
                    url_type = '%sURL' % iface['type']
                    v2_endpoint.setdefault('urls', []).append(
                        {'type': url_type, 'url': iface['url']})
                    v2_endpoint['service_type'] = service['type']

                v3_endpoint = {
                    'id': uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        '%(id)s-%(type)' % {'id': eid,
                                            'type': iface['type']}
                    ).hex,
                    'interface': iface['type'],
                    'url': iface['url'],
                    'service_id': service_id,
                    'service_type': service['type'],
                    'version': 3,
                    'legacy_endpoint_id': eid}
                if region is not None:
                    v3_endpoint['region'] = region
                    v2_endpoint['region'] = region

                catalog_eps = [v3_endpoint['id']] = v3_endpoint
            catalog_eps[v2_endpoint['id']] = v2_endpoint

    def _build_region_data(self, data):
        regions = {}
        for rid, region in data.items():
            valid_keys = ('description', 'parent_region_id')
            r_data = {'id': rid}
            # Ensure we are working with a dict instead of a None.
            # Regions need to be dicts loaded from the yaml
            for k in valid_keys:
                if k in region:
                    r_data[k] = region[k]
            regions[rid] = r_data
        return regions

    def _build_service_data(self, data):
        services = {}
        for sid, service in data:
            s_data = {'id': sid}
            try:
                s_data['type'] = service['type']
            except KeyError:
                raise ValueError(_(
                    'Service `%(service_id)s` must have a type.') %
                    {'service_id': sid})
            services[sid] = s_data
        return services

    def list_regions(self, hints):
        return self.__catalog_data['regions']

    def get_region(self, region_id):
        try:
            return self.__catalog_data['regions'][region_id]
        except KeyError:
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
        # NOTE(morgan): only send "v3" version, the controller will correct
        # the data to look like V2 if needed.
        return {e['id']: e
                for e in self.__catalog_data['endpoints'] if e['version'] == 3}

    def get_endpoint(self, endpoint_id):
        c_data_endpoints = self.__catalog_data.get('endpoints', {})
        if endpoint_id in c_data_endpoints:
            return self._build_endpoint_data(
                endpoint_id, c_data_endpoints.get(endpoint_id, {}) or {})

    def list_services(self, hints):
        return self.__catalog_data['services']

    def get_service(self, service_id):
        try:
            return self.__catalog_data['services']['service_id']
        except KeyError:
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
        silent_keyerror_failures = []
        if project_id:
            substitutions.update(
                {'tenant_id': project_id, 'project_id': project_id})
        else:
            silent_keyerror_failures = ['tenant_id', 'project_id']

        catalog = {}
        for eid, endpoint in (
                self.__catalog_data.get('endpoints') or {}).items():
            if endpoint['version'] != 2:
                continue

            service_data = endpoint.copy()
            urls = service_data.pop('urls')
            service_data.pop('version')
            stype = service_data.pop('service_type')
            region = service_data.pop('region')
            for u in urls:
                u_type = u['type']
                try:
                    formatted_url = utils.format_url(
                        u['url'], substitutions,
                        silent_keyerror_failures=silent_keyerror_failures)
                    if formatted_url is None:
                        continue
                except exception.MalformedEndpoint:  # nosec
                    continue  # this failure is already logged in format_url()
                catalog.setdefault(region, {}).setdefault(stype, {})[
                    u_type] = formatted_url
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
        for eid, endpoint in (
                self.__catalog_data.get('endpoints') or {}).items():
            if endpoint['version'] != 3:
                continue

            stype = endpoint['service_type']
            ep_rendered = {'interface': endpoint['interface'],
                           'id': endpoint['id'],
                           'region': endpoint['region']}
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
                s_rendered = services_rendered.setdefault(
                    sid, {'id': sid, 'type': stype, 'endpoints': []})
                catalog.append(s_rendered)
            else:
                s_rendered = services_rendered[sid]

            s_rendered['endpoints'].append(ep_rendered)

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
