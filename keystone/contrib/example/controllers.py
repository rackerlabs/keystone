# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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
from keystone.openstack.common import log as logging


LOG = logging.getLogger(__name__)

message_received_count = 0


@dependency.requires('example_api')
class ExampleV3Controller(controller.V3Controller):

    @controller.protected()
    def example_get(self, context):
        """Description of the controller logic."""
        self.example_api.do_something(context)

    @classmethod
    def project_deleted_notification(self, context, message):
        """The code below is merely an example."""
        global message_received_count
        message_received_count += 1
        msg = _('Received message id: %(message)s of type %(message_type)s'
                ' as received message number %(messages)s')
        LOG.info(msg, {'message': message.get('message_id'),
                       'message_type': message.get('event_type'),
                       'messages': str(message_received_count)})

    @classmethod
    def project_created_notification(self, context, message):
        """The code below is merely an example."""
        global message_received_count
        message_received_count += 1
        msg = _('Received message id: %(message)s of type %(message_type)s'
                ' as received message number %(messages)s')
        LOG.info(msg, {'message': message.get('message_id'),
                       'message_type': message.get('event_type'),
                       'messages': str(message_received_count)})
