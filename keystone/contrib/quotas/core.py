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
from keystone.common import extension
from keystone.common import manager
from keystone.common import wsgi


extension.register_admin_extension(
    'OS-QUOTAS', {
        'name': 'OpenStack Keystone Quotas',
        'namespace': 'http://docs.openstack.org/identity/api/ext/'
                     'OS-QUOTAS/v1.0',
        'alias': 'OS-QUOTAS',
        'updated': '2013-07-11T17:14:00-00:00',
        'description': 'OpenStack extensions to Keystone v3.0 API '
                       'enabling Administrative Operations.',
        'links': [
            {
                'rel': 'describedby',
                'type': 'text/html',
                'href': 'https://github.com/openstack/identity-api',
            }
        ]})


@dependency.provider('quotas_api')
class Manager(manager.Manager):

    def __init__(self):
        super(Manager, self).__init__('keystone.contrib.quotas.backends.sql.SQLQuotaDriver')


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
    def create_quota(self, context, project_id, quota):
        self.identity_api.driver.get_project(project_id)
        resource_id = quota.get('resource_id')
        if not resource_id:
            raise Exception('Bad request')
        self.quotas_api.driver.get_resource(resource_id)

        ref = self.quotas_api.driver.create_project_quota(project_id, quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def get_quota(self, context, project_id, quota_id):
        ref = self.quotas_api.driver.get_project_quota(user_id, quota_id)
        return self.wrap_member(context, ref)

    @controller.protected
    def update_quota(self, context, project_id, quota_id, quota):
        ref = self.quotas_api.driver.update_project_quota(project_id,
                                                       quota_id,
                                                       quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def delete_quota(self, context, project_id, quota_id):
        self.quotas_api.driver.delete_project_quota(project_id, quota_id)

    @controller.filterprotected('resource_id')
    def list_quotas(self, context, filters, project_id):
        refs = self.quotas_api.driver.list_project_quotas(project_id)
        return self.wrap_collection(context, refs, filters)


@dependency.requires('quotas_api')
class UserQuotaV3(controller.V3Controller):

    collection_name = 'quotas'
    member_name = 'quota'

    @controller.protected
    def create_quota(self, context, user_id, quota):
        self.identity_api.driver.get_user(user_id)
        resource_id = quota.get('resource_id')
        if not resource_id:
            raise Exception('Bad request')
        self.quotas_api.driver.get_resource(resource_id)

        ref = self.quotas_api.driver.create_user_quota(user_id, quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def get_quota(self, context, user_id, quota_id):
        ref = self.quotas_api.driver.get_user_quota(user_id, quota_id)
        return self.wrap_member(context, ref)

    @controller.protected
    def update_quota(self, context, user_id, quota_id, quota):
        ref = self.quotas_api.driver.update_user_quota(user_id,
                                                       quota_id,
                                                       quota)
        return self.wrap_member(context, ref)

    @controller.protected
    def delete_quota(self, context, user_id, quota_id):
        self.quotas_api.driver.delete_user_quota(user_id, quota_id)

    @controller.filterprotected('resource_id')
    def list_quotas(self, context, filters, user_id):
        refs = self.quotas_api.driver.list_user_quotas(user_id)
        return self.wrap_collection(context, refs, filters)


class QuotasExtention(wsgi.ExtensionRouter):

    def add_routes(self, mapper):
        resource_controller = ResourceV3()
        user_quota_controller = UserQuotaV3()
        project_quota_controller = ProjectQuotaV3()

        # resource oerations
        mapper.connect(
            '/OS-QUOTAS/resources',
            controller=resource_controller,
            action='create_resource',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/OS-QUOTAS/resources/{resource_id}',
            controller=resource_controller,
            action='get_resource',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-QUOTAS/resources/{resource_id}',
            controller=resource_controller,
            action='update_resource',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/OS-QUOTAS/resources/{resource_id}',
            controller=resource_controller,
            action='delete_resource',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/OS-QUOTAS/resources',
            controller=resource_controller,
            action='list_resources',
            conditions=dict(method=['GET']))

        # user quota operations
        mapper.connect(
            '/user/{user_id}/OS-QUOTAS/quotas',
            controller=user_quota_controller,
            action='create_quota',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/user/{user_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=user_quota_controller,
            action='get_quota',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/user/{user_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=user_quota_controller,
            action='update_quota',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/user/{user_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=user_quota_controller,
            action='delete_quota',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/user/{user_id}/OS-QUOTAS/quotas',
            controller=user_quota_controller,
            action='list_quotas',
            conditions=dict(method=['GET']))

        # project quota operations
        mapper.connect(
            '/project/{project_id}/OS-QUOTAS/quotas',
            controller=project_quota_controller,
            action='create_quota',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/project/{project_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=project_quota_controller,
            action='get_quota',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/project/{project_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=resource_controller,
            action='update_quota',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/project/{project_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=project_quota_controller,
            action='delete_quota',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/project/{project_id}/OS-QUOTAS/quotas',
            controller=project_quota_controller,
            action='list_quotas',
            conditions=dict(method=['GET']))
