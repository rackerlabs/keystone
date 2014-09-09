# Copyright 2012 OpenStack Foundationc
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

import os.path

import six

from keystone.catalog.backends import kvs
from keystone.catalog import core
from keystone import config
from keystone import exception
from keystone.i18n import _LC
from keystone.openstack.common import log


LOG = log.getLogger(__name__)

CONF = config.CONF


def parse_templates(template_lines):
    o = {}
    for line in template_lines:
        if ' = ' not in line:
            continue

        k, v = line.strip().split(' = ')
        if not k.startswith('catalog.'):
            continue

        parts = k.split('.')

        region = parts[1]
        # NOTE(termie): object-store insists on having a dash
        service = parts[2].replace('_', '-').rstrip()
        key = parts[3].rstrip()

        region_ref = o.get(region, {})
        service_ref = region_ref.get(service, {})
        service_ref[key] = v

        region_ref[service] = service_ref
        o[region] = region_ref

    return o


class Catalog(kvs.Catalog):
    """A backend that generates endpoints for the Catalog based on templates.

    It is usually configured via config entries that look like:

      catalog.$REGION.$SERVICE.$key = $value

    and is stored in a similar looking hierarchy. Where a value can contain
    values to be interpolated by standard python string interpolation that look
    like (the % is replaced by a $ due to paste attempting to interpolate on
    its own:

      http://localhost:$(public_port)s/

    When expanding the template it will pass in a dict made up of the conf
    instance plus a few additional key-values, notably tenant_id and user_id.

    It does not care what the keys and values are but it is worth noting that
    keystone_compat will expect certain keys to be there so that it can munge
    them into the output format keystone expects. These keys are:

      name - the name of the service, most likely repeated for all services of
             the same type, across regions.

      adminURL - the url of the admin endpoint

      publicURL - the url of the public endpoint

      internalURL - the url of the internal endpoint

    """

    service_properties = ['id', 'enabled', 'type', 'name', 'description']
    endpoint_properties = ['id', 'enabled', 'interface', 'region',
                           'service_id', 'url']

    def __init__(self, templates=None):
        super(Catalog, self).__init__()
        if templates:
            self.templates = templates
        else:
            template_file = CONF.catalog.template_file
            if not os.path.exists(template_file):
                template_file = CONF.find_file(template_file)
            self._load_templates(template_file)

    def _load_templates(self, template_file):
        try:
            self.templates = parse_templates(open(template_file))
        except IOError:
            LOG.critical(_LC('Unable to open template file %s'), template_file)
            raise

    def get_catalog(self, user_id, tenant_id, metadata=None):
        substitutions = dict(six.iteritems(CONF))
        substitutions.update({'tenant_id': tenant_id, 'user_id': user_id})

        catalog = {}
        for region, region_ref in six.iteritems(self.templates):
            catalog[region] = {}
            for service, service_ref in six.iteritems(region_ref):
                service_data = {}
                try:
                    for k, v in six.iteritems(service_ref):
                        service_data[k] = core.format_url(v, substitutions)
                except exception.MalformedEndpoint:
                    continue  # this failure is already logged in format_url()
                catalog[region][service] = service_data

        return catalog

    # Region CRUD

    def create_region(self, region):
        raise exception.NotImplemented()

    def get_region(self, region_id):
        region_list = self.list_regions()
        for region in region_list:
            if region['id'] == region_id:
                return region
        raise exception.RegionNotFound(region_id=region_id)

    def list_regions(self, hints=None):
        region_list = []
        for region, region_ref in six.iteritems(self.templates):
            reg_ref = {'id': region, 'description': '',
                       'parent_region_id': '', }
            region_list.append(reg_ref)
        return region_list

    def delete_region(self, region_id):
        raise exception.NotImplemented()

    def update_region(self, region_id, region):
        raise exception.NotImplemented()

    # Endpoint CRUD

    def create_endpoint(self, endpoint_id, endpoint):
        raise exception.NotImplemented()

    def get_endpoint(self, endpoint_id):
        endpoint_list = self.list_endpoints()
        for endpoint in endpoint_list:
            if endpoint['id'] == endpoint_id:
                return endpoint
        raise exception.EndpointNotFound(endpoint_id=endpoint_id)

    def update_endpoint(self, endpoint_id, endpoint):
        raise exception.NotImplemented()

    def delete_endpoint(self, endpoint_id):
        raise exception.NotImplemented()

    def _extract_interface_from_string(self, line):
        """Function used to obtain the value of 'url' in
        default_catalog.templates line

        Here we recive a line like:
            catalog.RegionOne.compute.internalURL =
                http://%SERVICE_HOST%:8774/v2/$(tenant_id)s
        And the function return the value:
           http://%SERVICE_HOST%:8774/v2/$(tenant_id)s

        :param line: Line from default_catalog.templates file
        :type line: string
        :returns: URL value as string
        """
        if 'URL' in line:
            return line.split('URL')[0]
        return None

    def list_endpoints(self, hints=None):
        endpoint_list = []
        # (marcos-fermin-lobo) There are no 'id' parameteres on
        # default_catalog.templates specification and the clients are
        # expecting 'id' parameter so, here we would use a simple counter.
        endpoint_id = 1
        service_id = 1
        service_dict = {}
        for region, region_ref in six.iteritems(self.templates):
            for service, service_ref in six.iteritems(region_ref):
                dict = {'id': str(endpoint_id), 'region': region,
                        'region_id': region, 'enabled': True,
                        'legacy_endpoint_id': endpoint_id, }
                for k, v in six.iteritems(service_ref):
                    if k in self.endpoint_properties:
                        dict[k] = v
                    else:
                        # (marcos-fermin-lobo) If k has 'URL' sub-string, we
                        # split the string and obtain the 'interface' and
                        # the 'url' values.
                        interface = self._extract_interface_from_string(k)
                        if interface is not None:
                            dict['interface'] = interface
                            dict[k.lower()] = v
                            # Backward compatible client V2
                            dict['url'] = v
                if service not in service_dict:
                    service_dict[service] = service_id
                    service_id += 1
                dict['service_id'] = str(service_dict[service])
                endpoint_list.append(dict)
                endpoint_id += 1
        return endpoint_list

    # Service CRUD

    def create_service(self, service_id, service):
        raise exception.NotImplemented()

    def list_services(self, hints=None):
        service_dict = {}
        # (marcos-fermin-lobo) There are no 'id' parameters on
        # default_catalog.templates specification and the clients are
        # expecting 'id' parameter so, here we would use a simple counter.
        id = 1
        for region, region_ref in six.iteritems(self.templates):
            for service, service_ref in six.iteritems(region_ref):
                dict = {'id': str(id), 'type': service, 'enabled': True,
                        'description': '', }
                for k, v in six.iteritems(service_ref):
                    if k in self.service_properties:
                        dict[k] = v
                if service not in service_dict:
                    service_dict[service] = dict
                    id += 1

        return list(service_dict.values())

    def get_service(self, service_id):
        service_list = self.list_services()
        for service in service_list:
            if service['id'] == service_id:
                return service
        raise exception.ServiceNotFound(service_id=service_id)

    def update_service(self, service_id, service):
        raise exception.NotImplemented()

    def delete_service(self, service_id):
        raise exception.NotImplemented()
