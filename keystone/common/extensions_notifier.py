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

SUBSCRIBERS = {}


class InvalidEventError(ValueError):
    pass


class InvalidResourceTypeError(ValueError):
    pass


def _get_callback_info(callback):
    if getattr(callback, 'im_class', None):
        return [getattr(callback, '__module__', None),
                callback.im_class.__name__,
                callback.__name__]
    else:
        return [getattr(callback, '__module__', None), callback.__name__]


def register(event, resource_type, callbacks):
    """Registers all the extensions listening to a specific event."""
    global SUBSCRIBERS
    if event not in notifications.ACTIONS:
        raise InvalidEventError(_('%(event)s is not a valid notification '
                                  'event, must be one of: %(actions)s'),
                                {'event': event,
                                 'actions': ', '.join(notifications.ACTIONS)})
    if resource_type not in notifications.RESOURCE_TYPES:
        raise InvalidResourceTypeError(_('%(resource_type)s is not a valid '
                                         'notification resource, must be one '
                                         'of: %(types)s'),
                                       {'resource_type': resource_type,
                                        'types': ', '.join(
                                            notifications.RESOURCE_TYPES)})

    if not hasattr(callbacks, '__iter__'):
        callbacks = [callbacks]

    for callback in callbacks:
        if not callable(callback):
            LOG.error(_('Method not callable: %s'), callback)
            continue
        SUBSCRIBERS.setdefault(event, {}).setdefault(resource_type, set())
        SUBSCRIBERS[event][resource_type].add(callback)

        if LOG.logger.getEffectiveLevel() < 20:
            # for Python logging, INFO level is 20. Do this only if its going
            # to appear in the logs.
            msg = _('Callback: `%(callback)s` subscribed to event '
                    '`%(event)s`.')
            callback_info = _get_callback_info(callback)
            callback_str = '.'.join(
                filter(lambda i: i is not None, callback_info))
            event_str = '.'.join(['identity', resource_type, event])
            LOG.info(msg, {'callback': callback_str, 'event': event_str})


def notify(context, message):
    """Sends a notification to registered extensions."""
    if not context:
        context = req_context.get_admin_context()
    event = message.get('event_type')
    event_type, resource_type, operation = event.split('.')

    if operation in SUBSCRIBERS:
        if resource_type in SUBSCRIBERS[operation]:
            for cb in SUBSCRIBERS[operation][resource_type]:
                LOG.debug('invoking callback %(cb_name)s for event %(event)s',
                          {'cb_name': cb.__name__, 'event': event})
                cb(context, message)
