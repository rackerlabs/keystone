# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 IBM Corp.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

from keystone import notifications
from keystone.tests import core as test


class NotificationsTestCase(test.TestCase):

    def setUp(self):
        super(NotificationsTestCase, self).setUp()

    def test_send_update_project_created(self):
        """Test to ensure event_type is 'identity.project.created'."""

        old_res = None
        new_res = 'new_resource_information'

        def fake_update_notification(resource, event_type, service="identity",
                                     host=None):
            exp_event = 'identity.project.created'
            self.assertEqual(exp_event, event_type)
            exp_res = 'new_resource_information'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_update_notification',
                       fake_update_notification)
        notifications.send_update(old_res, new_res, 'project')

    def test_send_update_project_updated(self):
        """Test to ensure event_type is 'identity.project.updated'."""

        old_res = 'old_resource_information'
        new_res = 'new_resource_information'

        def fake_update_notification(resource, event_type, service="identity",
                                     host=None):
            exp_event = 'identity.project.updated'
            self.assertEqual(exp_event, event_type)
            exp_res = 'new_resource_information'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_update_notification',
                       fake_update_notification)
        notifications.send_update(old_res, new_res, 'project')

    def test_send_update_project_deleted(self):
        """Test to ensure event_type is 'identity.project.deleted'."""

        old_res = 'old_resource_information'
        new_res = None

        def fake_update_notification(resource, event_type, service="identity",
                                     host=None):
            exp_event = 'identity.project.deleted'
            self.assertEqual(exp_event, event_type)
            exp_res = 'old_resource_information'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_update_notification',
                       fake_update_notification)
        notifications.send_update(old_res, new_res, 'project')
