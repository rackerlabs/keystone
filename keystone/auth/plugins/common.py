# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

from keystone.common import logging
from keystone import exception

LOG = logging.getLogger(__name__)


def lookup_domain(context, domain_info, identity_api):
    domain_id = domain_info.get('id')
    domain_name = domain_info.get('name')
    domain_ref = None

    if not domain_id and not domain_name:
        raise exception.ValidationError(attribute='id or name',
                                        target='domain')
    try:
        if domain_name:
            domain_ref = identity_api.get_domain_by_name(
                context=context, domain_name=domain_name)
        else:
            domain_ref = identity_api.get_domain(
                context=context, domain_id=domain_id)
    except exception.DomainNotFound as e:
        LOG.exception(e)
        raise exception.Unauthorized(e)
    assert_domain_is_enabled(domain_ref)
    return domain_ref


def assert_domain_is_enabled(domain_ref):
    if not domain_ref.get('enabled'):
        msg = _('Domain is disabled: %s') % (domain_ref['id'])
        LOG.warning(msg)
        raise exception.Unauthorized(msg)
