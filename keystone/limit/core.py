# Copyright 2017 SUSE Linux Gmbh
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

from keystone.common import driver_hints
from keystone.common import manager
import keystone.conf
from keystone import exception


CONF = keystone.conf.CONF


class RegisteredLimitManager(manager.Manager):

    driver_namespace = 'keystone.registered_limit'
    _provides_api = 'registered_limit_api'

    def __init__(self):
        super(RegisteredLimitManager, self).__init__('sql')

    def _assert_resource_exist(self, registered_limit):
        service_id = registered_limit.get('service_id')
        region_id = registered_limit.get('region_id')
        try:
            if service_id is not None:
                self.catalog_api.get_service(service_id)
            if region_id is not None:
                self.catalog_api.get_region(region_id)
        except exception.ServiceNotFound:
            raise exception.ValidationError(attribute='service_id',
                                            target='registered_limits')
        except exception.RegionNotFound:
            raise exception.ValidationError(attribute='region_id',
                                            target='registered_limits')

    def create_registered_limits(self, registered_limits):
        for registered_limit in registered_limits:
            self._assert_resource_exist(registered_limit)
            if registered_limit.get('region_id') is None:
                self.driver.check_registered_limit_duplicated(registered_limit)
        return self.driver.create_registered_limits(registered_limits)

    def update_registered_limits(self, registered_limits):
        for registered_limit in registered_limits:
            self._assert_resource_exist(registered_limit)
        self.driver.update_registered_limits(registered_limits)
        return self.driver.list_registered_limits(driver_hints.Hints())

    @manager.response_truncated
    def list_registered_limits(self, hints=None):
        return self.driver.list_registered_limits(
            hints or driver_hints.Hints())

    def get_registered_limit(self, registered_limit_id):
        return self.driver.get_registered_limit(registered_limit_id)

    def delete_registered_limit(self, registered_limit_id):
        return self.driver.delete_registered_limit(registered_limit_id)

    def check_reference_exist(self, limit):
        return self.driver.check_reference_exist(limit)


class LimitManager(manager.Manager):

    driver_namespace = 'keystone.limit'
    _provides_api = 'limit_api'

    def __init__(self):
        super(LimitManager, self).__init__('sql')

    def _assert_resource_exist(self, limit):
        try:
            self.catalog_api.get_service(limit['service_id'])
            region_id = limit.get('region_id')
            if region_id is not None:
                self.catalog_api.get_region(region_id)
            self.resource_api.get_project(limit['project_id'])
        except exception.ServiceNotFound:
            raise exception.ValidationError(attribute='service_id',
                                            target='limits')
        except exception.RegionNotFound:
            raise exception.ValidationError(attribute='region_id',
                                            target='limits')
        except exception.ProjectNotFound:
            raise exception.ValidationError(attribute='project_id',
                                            target='limits')

    def create_limits(self, limits):
        for limit in limits:
            self._assert_resource_exist(limit)
            if limit.get('region_id') is None:
                self.registered_limit_api.check_reference_exist(limit)
                self.driver.check_limit_duplicated(limit)
        return self.driver.create_limits(limits)

    def update_limits(self, limits, project_id):
        self.driver.update_limits(limits)
        return self.list_limits(driver_hints.Hints(), project_id)

    @manager.response_truncated
    def list_limits(self, hints, project_id):
        return self.driver.list_limits(hints or driver_hints.Hints(),
                                       project_id)

    def get_limit(self, limit_id):
        return self.driver.get_limit(limit_id)

    def delete_limit(self, limit_id):
        return self.driver.delete_limit(limit_id)
