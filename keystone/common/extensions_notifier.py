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

from keystone import notifications
from keystone.openstack.common import context as req_context
from keystone.openstack.common import log as logging


LOG = logging.getLogger(__name__)

subscribers = {}


def register(event, resource_type, callbacks):
    """Registers all the extensions listening to a specific event."""
    global subscribers
    if event not in notifications.ACTIONS:
        raise ValueError(_('%(event)s is not a valid notification event, '
                           'must be one of: %(actions)s'),
                         {'event': event,
                          'actions': ', '.join(notifications.ACTIONS)})
    if resource_type not in notifications.RESOURCE_TYPES:
        raise ValueError(_('%(resource_type)s is not a valid notification '
                           'resource, must be one of: %(types)s'),
                         {'resource_type': resource_type,
                          'types': ', '.join(notifications.TYPES)})

    if not hasattr(callbacks, '__iter__'):
        callbacks = [callbacks]

    for cb in callbacks:
        if not callable(cb):
            LOG.error(_('Method not callable: %s'), cb)
            continue
        subscribers.setdefault(event, {}).setdefault(resource_type, set())
        subscribers[event][resource_type].add(cb)

        msg = _('Callback: `%(callback)s` subscribed to event `%(event)s`.')
        if getattr(cb, 'im_class', None):
            cb_info = [getattr(cb, '__module__', None), cb.im_class.__name__,
                       cb.__name__]
        else:
            cb_info = [getattr(cb, '__module__', None), cb.__name__]
        cb_str = '.'.join(filter(lambda i: i is not None, cb_info))
        event_str = '.'.join(['identity', resource_type, event])
        LOG.info(msg, {'callback': cb_str, 'event': event_str})


def notify(context, message):
    """Sends a notification to registered extensions."""
    if not context:
        context = req_context.get_admin_context()
    event = message.get('event_type')
    event_type, resource_type, operation = event.split('.')

    if operation in subscribers:
        if resource_type in subscribers[operation]:
            for cb in subscribers[operation][resource_type]:
                LOG.debug('invoking callback %(cb_name)s for event %(event)s',
                          {'cb_name': cb.__name__, 'event': event})
                cb(context, message)
