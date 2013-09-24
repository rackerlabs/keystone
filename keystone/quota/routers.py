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

""" WSGI Routes for quota."""

from keystone.quota import controllers


def append_v3_routers(mapper, routers):
    quota_controller = controllers.DomainQuota()

    mapper.connect('/domains/{domain_id}/quotas',
                   controller=quota_controller,
                   action='get_domain_quotas_for_region',
                   conditions=dict(method=['GET']))

    mapper.connect('/domains/{domain_id}/quotas',
                   controller=quota_controller,
                   action='update_domain_quotas_in_region',
                   conditions=dict(method=['PUT']))

    mapper.connect('/domains/{domain_id}/quotas',
                   controller=quota_controller,
                   action='delete_domain_quotas_from_region',
                   conditions=dict(method=['DELETE']))
