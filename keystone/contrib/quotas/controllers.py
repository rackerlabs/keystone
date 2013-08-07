# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

from keystone.common import controller
from keystone.common import dependency


@dependency.requires('quotas_api')
class ResourceV3(controller.V3Controller):

    collection_name = 'resources'
    member_name = 'resource'

    @controller.protected
    def create_resource(self, context, resource):
        ref = self.quotas_api.driver.create_resource(resource)
        return self.wrap_member(context, ref)

    @controller.protected
    def get_resource(self, context, resource_id):
        ref = self.quotas_api.driver.get_resource(resource_id)
        return self.wrap_member(context, ref)

    @controller.protected
    def update_resource(self, context, resource_id, resource=None):
        ref = self.quotas_api.driver.update_resource(resource_id, resource)
        return self.wrap_member(context, ref)

    @controller.protected
    def delete_resource(self, context, resource_id):
        self.quotas_api.driver.delete_resource(resource_id)

    @controller.filterprotected('name')
    def list_resources(self, context, filters):
        refs = self.quotas_api.driver.list_resources()
        return self.wrap_collection(context, refs, filters)


@dependency.requires('quotas_api')
class ProjectQuotaV3(controller.V3Controller):

    collection_name = 'quotas'
    member_name = 'quota'

    @controller.protected
    def create_project_quota(self, context, project_id, quota):
        self.assignment_api.driver.get_project(project_id)
        resource_id = quota.get('resource_id')
        if not resource_id:
            raise Exception('Bad request')
        self.quotas_api.driver.get_resource(resource_id)

        ref = self.quotas_api.driver.create_project_quota(project_id, quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def get_project_quota(self, context, project_id, quota_id):
        ref = self.quotas_api.driver.get_project_quota(project_id, quota_id)
        return self.wrap_member(context, ref)

    @controller.protected
    def update_project_quota(self, context, project_id, quota_id, quota):
        ref = self.quotas_api.driver.update_project_quota(project_id,
                                                          quota_id,
                                                          quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def delete_project_quota(self, context, project_id, quota_id):
        self.quotas_api.driver.delete_project_quota(project_id, quota_id)

    @controller.filterprotected('resource_id')
    def list_project_quotas(self, context, filters, project_id):
        refs = self.quotas_api.driver.list_project_quotas(project_id)
        return self.wrap_collection(context, refs, filters)


@dependency.requires('quotas_api')
class UserQuotaV3(controller.V3Controller):

    collection_name = 'quotas'
    member_name = 'quota'

    @controller.protected
    def create_user_quota(self, context, user_id, quota):
        self.identity_api.driver.get_user(user_id)
        resource_id = quota.get('resource_id')
        if not resource_id:
            raise Exception('Bad request')
        self.quotas_api.driver.get_resource(resource_id)

        ref = self.quotas_api.driver.create_user_quota(user_id, quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def get_user_quota(self, context, user_id, quota_id):
        ref = self.quotas_api.driver.get_user_quota(user_id, quota_id)
        return self.wrap_member(context, ref)

    @controller.protected
    def update_user_quota(self, context, user_id, quota_id, quota):
        ref = self.quotas_api.driver.update_user_quota(user_id,
                                                       quota_id,
                                                       quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def delete_user_quota(self, context, user_id, quota_id):
        self.quotas_api.driver.delete_user_quota(user_id, quota_id)

    @controller.filterprotected('resource_id')
    def list_user_quotas(self, context, filters, user_id):
        refs = self.quotas_api.driver.list_user_quotas(user_id)
        return self.wrap_collection(context, refs, filters)
