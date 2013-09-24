# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 OpenStack LLC

#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""WSGI Routers for the Identity service."""


from keystone.common import controller
from keystone.common import dependency
from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging

CONF = config.CONF
LOG = logging.getLogger(__name__)


@dependency.requires('quota_api')
class DomainQuota(controller.V3Controller):
    collection_name = "quotas"
    member_name = "quota"

    def _concatenate_service_name(self, quotas, service_name):
        new_dict = {}
        for resource_name, v in quotas.iteritems():
            new_key = service_name + '.' + resource_name
            new_dict[new_key] = v
        return new_dict

    def _user_info_to_dict(self, context):
        token_id = context['token_id']
        token = self.token_api.get_token(token_id)
        user_id = token['user_id']
        return {"user_id": user_id, "role": "admin"}

    def _cloud_admin_info_to_dict(self, context, domain_id):
        return {"role": "admin"}

    def _get_default_values(self, domain_id, region_name, minus, servs):
        child = dict(domain_id=domain_id, region=region_name)
        services = minus.keys()

        if not services:
            services = servs

        defaults = dict()
        if 'nova' in services:
            nova = dict()
            for option, value in CONF.nova.iteritems():
                if (not minus) or (option not in minus['nova'].keys()):
                    nova[option] = value
                else:
                    nova[option] = minus['nova'][option]
            defaults['nova'] = nova
        if 'cinder' in services:
            cinder = dict()
            for option, value in CONF.cinder.interitems():
                if (not minus) or (option not in minus['cinder'].keys()):
                    cinder[option] = value
                else:
                    cinder[option] = minus['cinder'][option]
            defaults['cinder'] = cinder
        if 'neutron' in services:
            neutron = dict()
            for option, value in CONF.neutron.interitems():
                if (not minus) or (option not in minus['neutron'].keys()):
                    neutron[option] = value
                else:
                    neutron[option] = minus['neutron'][option]
            defaults['neutron'] = neutron

        return list(list([child, defaults]))

    @controller.protected()
    def get_domain_quotas_for_region(self, context, domain_id,
                                     quotas=None):
        """Get quotas from domain_id by region."""
        if quotas is None:
            raise exception.ValidationError(attribute="quotas",
                                            target="request")

        domain = self.identity_api.get_domain(domain_id)
        if domain is None:
            raise exception.DomainNotFound(domain_id)

        self._require_attribute(quotas, 'region')
        self._require_attribute(quotas, 'services')
        region = quotas['region']
        services = quotas['services']

        #return ceilings
        ceilings = self.quota_api.get_domain_quota_by_services(services,
                                                               domain_id,
                                                               region)
        result = self._get_default_values(domain_id, region, ceilings,
                                          services)
        return result

    @controller.protected()
    def update_domain_quotas_in_region(self, context, domain_id,
                                       quotas=None):
        """Updates quotas."""
        if quotas is None:
            raise exception.ValidationError(attribute='quotas',
                                            target='request')

        domain = self.identity_api.get_domain(domain_id)
        if domain is None:
            raise exception.DomainNotFound(domain_id)

        self._require_attribute(quotas, 'region')
        region = quotas['region']

        quotas_to_update = {}
        services = list()
        if "nova" in quotas:
            quotas_to_update.update(self._concatenate_service_name(
                quotas['nova'], 'nova'))
            services.append("nova")

        if "cinder" in quotas:
            quotas_to_update.update(self._concatenate_service_name(
                quotas['cinder'], 'cinder'))
            services.append("cinder")

        if "neutron" in quotas:
            quotas_to_update.update(self._concatenate_service_name(
                quotas['neutron'], 'neutron'))
            services.append("neutron")

        created_by = self._user_info_to_dict(context)
        parent_data = self._cloud_admin_info_to_dict(context, domain_id)
        try:
            #update
            for resource, new_ceiling in quotas_to_update.iteritems():
                self.quota_api.set_domain_quota(resource, new_ceiling,
                                                domain_id, region, parent_data,
                                                created_by)

            ceilings = self.quota_api.get_domain_quota_by_services(services,
                                                                   domain_id,
                                                                   region)
            result = self._get_default_values(domain_id, region, ceilings,
                                              services)
            return result
        except exception.Error as error:
            raise error

    @controller.protected()
    def delete_domain_quotas_from_region(self, context, domain_id,
                                         quotas=None):
        """Deletes all quotas of a service from a given domain."""
        if quotas is None:
            raise exception.ValidationError(attribute='quotas',
                                            target='request')

        domain = self.identity_api.get_domain(domain_id)
        if not domain:
            raise exception.DomainNotFound(domain_id)

        #get region and services to delete
        self._require_attribute(quotas, 'region')
        self._require_attribute(quotas, 'services')
        region = quotas['region']
        services = quotas['services']
        deleted_by = self._user_info_to_dict(context)

        try:
            #delete
            self.quota_api.delete_domain_quota(services, domain_id, region,
                                               deleted_by)

            ceilings = self.quota_api.get_domain_quota_by_services(services,
                                                                   domain_id,
                                                                   region)
            result = self._get_default_values(domain_id, region, ceilings,
                                              services)
            return result

        except exception.Error as error:
            raise error
