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


from keystone.contrib.example import controllers
from keystone.openstack.common.notifier import extensions_notifier

controller = controllers.ExampleV3Controller

subscribed_events = {
    'identity.project.deleted': controller.project_deleted_notification,
    'identity.project.created': controller.project_created_notification
}

extensions_notifier.register(subscribed_events)
