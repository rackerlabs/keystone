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
from keystone.openstack.common.notifier import api as notifier_api
from keystone.tests import core as test


class NotificationsTestCase(test.TestCase):

    def setUp(self):
        super(NotificationsTestCase, self).setUp()

    def test_send_notification_project_created(self):
        """Test to ensure event_type is 'identity.project.created'."""

        resource_id = 'created_resource_id'

        def fake_send_notification(resource, event_type, service='identity',
                                   host=None):
            exp_event = 'identity.project.created'
            self.assertEqual(exp_event, event_type)
            exp_res = 'created_resource_id'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_notification',
                       fake_send_notification)
        notifications.create_notification(resource_id, 'project')

    def test_send_notification_project_updated(self):
        """Test to ensure event_type is 'identity.project.updated'."""

        resource_id = 'updated_resource_id'

        def fake_send_notification(resource, event_type, service='identity',
                                   host=None):
            exp_event = 'identity.project.updated'
            self.assertEqual(exp_event, event_type)
            exp_res = 'updated_resource_id'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_notification',
                       fake_send_notification)
        notifications.update_notification(resource_id, 'project')

    def test_send_notification_project_deleted(self):
        """Test to ensure event_type is 'identity.project.deleted'."""

        resource_id = 'deleted_resource_id'

        def fake_send_notification(resource, event_type, service='identity',
                                   host=None):
            exp_event = 'identity.project.deleted'
            self.assertEqual(exp_event, event_type)
            exp_res = 'deleted_resource_id'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_notification',
                       fake_send_notification)
        notifications.delete_notification(resource_id, 'project')

    def test_send_notification(self):
        """Test the private method _send_notification."""

        resource = 'some_resource_id'
        event_type = 'identity.project.created'
        service = 'identity'
        host = None

        # NOTE(ldbragst): Even though notifications._send_notification doesn't
        # contain logic that creates cases, this is suppose to test that
        # context is always empty and that we ensure the resource ID of the
        # resource in the notification is contained in the payload. It was
        # agreed that context should be empty in Keystone's case, which is
        # also noted in the /keystone/notifications.py module. This test
        # ensures and maintains these conditions.
        def fake_notify(context, publisher_id, event_type, priority, payload):
            exp_context = {}
            self.assertEqual(exp_context, context)
            exp_payload = {'resource_info': 'some_resource_id'}
            self.assertEqual(exp_payload, payload)

        self.stubs.Set(notifier_api, 'notify', fake_notify)
        notifications._send_notification(resource, event_type, service, host)
