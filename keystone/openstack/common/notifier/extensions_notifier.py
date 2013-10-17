# Copyright 2011 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from oslo.config import cfg

from keystone.openstack.common import context as req_context
from keystone.openstack.common import log as logging
from keystone.openstack.common import rpc

LOG = logging.getLogger(__name__)

subscribers = {}

def register(subscriptions):
    """Registers all the extensions listening to specific events""" 
    global subscribers
    for subscription_event, subscription_callback in subscriptions.iteritems():
        subscribers.setdefault(subscription_event, { 'subscribers': [] })
        subscribers[subscription_event]['subscribers'].append(subscription_callback)

def notify(context, message):
    """Sends a notification to registered extensions."""
    if not context:
        context = req_context.get_admin_context()
    event = message.get('event_type')
    if event in subscribers.keys():
        for extension in subscribers[event]['subscribers']:
            extension(context, message)
