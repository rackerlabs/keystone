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


from keystone.common import dependency
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.openstack.common import log


CONF = config.CONF
LOG = log.getLogger(__name__)


@dependency.provider('example_api')
class ExampleManager(manager.Manager):
    """Example Manager.

    See :mod:`keystone.common.manager.Manager` for more details on
    how this dynamically calls the backend.

    """

    def __init__(self):
        # The following is an example of event callbacks. In this setup,
        # ExampleManager's data model is depended on project's data model.
        # It must create additional aggregates when a new project is created,
        # and it must cleanup data related to the project whenever a project
        # has been deleted.
        #
        # In this example, the project_deleted_callback will be involved
        # whenever a project has been deleted. Similarily, the
        # project_created_callback wil be invoked whenever a new project is
        # created.

        # This information is used when the @dependency.provider decorator acts
        # on the class.
        self.event_callbacks = {
            'deleted': {
                'project': [
                    self.project_deleted_callback]},
            'created': {
                'project': [
                    self.project_created_callback]}}
        super(ExampleManager, self).__init__(
            'keystone.contrib.example.core.ExampleDriver')

    def project_deleted_callback(self, context, message):
        # The code below is merely an example.
        msg = _('Received message id: %(message_id)s of type %(message_type)s'
                ' as received message number %(messages)s')
        LOG.info(msg, {'message_id': message.get('message_id'),
                       'message_type': message.get('event_type')})

    def project_created_callback(self, context, message):
        # The code below is merely an example.
        msg = _('Received message id: %(message_id)s of type %(message_type)s'
                ' as received message number %(messages)s')
        LOG.info(msg, {'message_id': message.get('message_id'),
                       'message_type': message.get('event_type')})


class ExampleDriver(object):
    """Interface description for Example driver."""

    def do_something(self, data):
        """Do something

        :param data: example data
        :type data: string
        :raises: keystone.exception,
        :returns: None.

        """
        raise exception.NotImplemented()
