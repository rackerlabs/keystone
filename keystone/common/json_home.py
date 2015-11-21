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

import functools

from keystone import exception
from keystone.i18n import _

DOC_URL = 'http://docs.openstack.org/api/openstack-identity/3'


def _create_doc_path(typ, ident, extension_name=None, extension_version=None):
    if extension_name:
        rel = '%s/ext/%s/%s/%s/%s' % (DOC_URL,
                                      extension_name,
                                      extension_version,
                                      typ,
                                      ident)
    else:
        rel = '%s/%s/%s' % (DOC_URL, typ, ident)

    return rel


build_v3_resource_relation = functools.partial(_create_doc_path, 'rel')
build_v3_parameter_relation = functools.partial(_create_doc_path, 'param')


class Parameters(object):
    """Relationships for Common parameters."""

    DOMAIN_ID = build_v3_parameter_relation('domain_id')
    ENDPOINT_ID = build_v3_parameter_relation('endpoint_id')
    GROUP_ID = build_v3_parameter_relation('group_id')
    POLICY_ID = build_v3_parameter_relation('policy_id')
    PROJECT_ID = build_v3_parameter_relation('project_id')
    REGION_ID = build_v3_parameter_relation('region_id')
    ROLE_ID = build_v3_parameter_relation('role_id')
    SERVICE_ID = build_v3_parameter_relation('service_id')
    USER_ID = build_v3_parameter_relation('user_id')


class Status(object):
    """Status values supported."""

    DEPRECATED = 'deprecated'
    EXPERIMENTAL = 'experimental'
    STABLE = 'stable'

    @classmethod
    def update_resource_data(cls, resource_data, status):
        if status is cls.STABLE:
            # We currently do not add a status if the resource is stable, the
            # absence of the status property can be taken as meaning that the
            # resource is stable.
            return
        if status is cls.DEPRECATED or status is cls.EXPERIMENTAL:
            resource_data['hints'] = {'status': status}
            return

        raise exception.Error(message=_(
            'Unexpected status requested for JSON Home response, %s') % status)


def translate_urls(json_home, new_prefix):
    """Given a JSON Home document, sticks new_prefix on each of the urls."""
    for dummy_rel, resource in json_home['resources'].items():
        if 'href' in resource:
            resource['href'] = new_prefix + resource['href']
        elif 'href-template' in resource:
            resource['href-template'] = new_prefix + resource['href-template']
