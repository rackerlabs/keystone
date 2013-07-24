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
from keystone.openstack.common.notifier import test_notifier as notifier_api
from keystone import test
#import unittest2 as unittest

class NotificationsTestCase(test.TestCase):


    def setUp(self):

        super(NotificationsTestCase, self).setUp()
        NOTIFICATIONS = notifier_api.NOTIFICATIONS

    def tearDown(self):

        NOTIFICATIONS = []

    def test_send_update_resource_created(self):
        """Test to ensure event_type is 'identity.resource.created'."""

        context = 'fake_context'
        old_res = None
        new_res = 'new_resource_information'

        def fake_update_notification(context, resource, event_type,
                                     service="identity", host=None):

            exp_event = 'identity.resource.created'
            self.assertEqual(exp_event, event_type)
            exp_res = 'new_resource_information'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_update_notification',
                       fake_update_notification)
        notifications.send_update(context, old_res, new_res)

    def test_send_update_resource_updated(self):
        """Test to ensure event_type is 'identity.resource.updated'."""

        context = 'fake_context'
        old_res = 'old_resource_information'
        new_res = 'new_resource_information'

        def fake_update_notification(context, resource, event_type,
                                     service="identity", host=None):

            exp_event = 'identity.resource.updated'
            self.assertEqual(exp_event, event_type)
            exp_res = 'new_resource_information'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_update_notification',
                       fake_update_notification)
        notifications.send_update(context, old_res, new_res)

    def test_send_update_resource_deleted(self):
        """Test to ensure event_type is 'identity.resource.deleted'."""

        context = 'fake_context'
        old_res = 'old_resource_information'
        new_res = None

        def fake_update_notification(context, resource, event_type,
                                     service="identity", host=None):

            exp_event = 'identity.resource.deleted'
            self.assertEqual(exp_event, event_type)
            exp_res = 'old_resource_information'
            self.assertEqual(exp_res, resource)

        self.stubs.Set(notifications, '_send_update_notification',
                       fake_update_notification)
        notifications.send_update(context, old_res, new_res)
