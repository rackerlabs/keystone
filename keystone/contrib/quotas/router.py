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

from keystone.common import wsgi
from keystone.contrib.quotas import controllers


class QuotasExtention(wsgi.ExtensionRouter):

    def add_routes(self, mapper):
        resource_controller = controllers.ResourceV3()
        user_quota_controller = controllers.UserQuotaV3()
        project_quota_controller = controllers.ProjectQuotaV3()

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
            '/users/{user_id}/OS-QUOTAS/quotas',
            controller=user_quota_controller,
            action='create_user_quota',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/users/{user_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=user_quota_controller,
            action='get_user_quota',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/users/{user_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=user_quota_controller,
            action='update_user_quota',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/users/{user_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=user_quota_controller,
            action='delete_user_quota',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/users/{user_id}/OS-QUOTAS/quotas',
            controller=user_quota_controller,
            action='list_user_quotas',
            conditions=dict(method=['GET']))

        # project quota operations
        mapper.connect(
            '/projects/{project_id}/OS-QUOTAS/quotas',
            controller=project_quota_controller,
            action='create_project_quota',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/projects/{project_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=project_quota_controller,
            action='get_project_quota',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/projects/{project_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=project_quota_controller,
            action='update_project_quota',
            conditions=dict(method=['PATCH']))

        mapper.connect(
            '/projects/{project_id}/OS-QUOTAS/quotas/{quota_id}',
            controller=project_quota_controller,
            action='delete_project_quota',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/projects/{project_id}/OS-QUOTAS/quotas',
            controller=project_quota_controller,
            action='list_project_quotas',
            conditions=dict(method=['GET']))
