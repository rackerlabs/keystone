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


class ExtensionV3Controller(controller.V3Controller):

    def __init__(self):
        super(ExtensionV3Controller, self).__init__()
        self.subscribed_events = None

    def subscriptions(self):
        """Return the list of events and associated callbacks."""
        return self.subscribed_events
