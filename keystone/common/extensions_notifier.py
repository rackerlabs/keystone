# Copyright 2013 OpenStack Foundation.
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


import re

from keystone.openstack.common import context as req_context
from keystone.openstack.common import log as logging

LOG = logging.getLogger(__name__)

subscribers = {}


def register(subscriptions):
    """Registers all the extensions listening to a specific event."""
    global subscribers
    pattern = '(identity.(group|project|role|user).(created|updated|deleted))'
    for subscription_event, subscription_callback in subscriptions.iteritems():
        if (callable(subscription_callback) and
                re.match(pattern, subscription_event)):
            subscribers.setdefault(subscription_event, {'subscribers': []})
            subscribers[subscription_event]['subscribers'].append(
                subscription_callback)
            msg = _('Callback: %(method)s of class %(class)s in module '
                    '%(module)s, subscribed to event %(event)s.')
            LOG.info(msg, {'method': subscription_callback.__name__,
                           'class': getattr(subscription_callback,
                                            '__class__', None),
                           'module': getattr(subscription_callback,
                                             '__module__', None),
                           'event': subscription_event})
        else:
            msg = _('Method not callable: %(method)s or %(event)s.'
                    'not recognized.')
            LOG.error(msg, {'method': subscription_callback,
                            'event': subscription_event})


def notify(context, message):
    """Sends a notification to registered extensions."""
    if not context:
        context = req_context.get_admin_context()
    event = message.get('event_type')
    if event in subscribers.keys():
        for extension in subscribers[event]['subscribers']:
            extension(context, message)
