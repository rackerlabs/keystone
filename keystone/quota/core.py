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

"""Main entry point into the Quota extension."""

from keystone.common import dependency
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging


CONF = config.CONF
LOG = logging.getLogger(__name__)


@dependency.provider('quota_api')
class Manager(manager.Manager):
    """Default pivot point for the Quota backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.
    """

    def __init__(self):
        super(Manager, self).__init__(CONF.quota.driver)


class Driver(object):
    def set_domain_quota(self, resource_name, ceiling, domain_id, region_name,
                         parent_data, created_by):
        """Updates the quota applicable to the specified child
       for the given resource.
       :param resource_name: name of the resource in the format
       <service-name>.<resouce-name>
       :param child: details of the entity for which quota is to be updated.
       It should be a dictionary
       :param ceiling_to_update_to: value of the quota to update to.
       :param parent_data: details of the entity calling this method. It
       should be a dictionary and should exactly match the parent_data
       already present in the db.
       """
        raise exception.NotImplemented()

    def delete_domain_quota(self, service_list, domain_id, region_name,
                            deleted_by):
        """Deletes quota applicable to the specified child for all the
        resources in service_list

        :param service_list: list of services
        :param child_data: details of the entity for which quota is to be
        delete. It should be a dictionary.
        :param parent_data: details of the entity calling this method. It
        should a dictionary and it should match the parent_data already
        present in DB.
        """
        raise exception.NotImplemented()

    def get_domain_quota_by_services(self, service_list, domain_id,
                                     region_name):
        """Gets the quota applicable to the specified child_data for all the
        resources in the given service_list.

        :param service_list: list of services
        :param child_data: details of the entity for which quota is requested.
        It should be a dictionary.
        """
        raise exception.NotImplemented()
