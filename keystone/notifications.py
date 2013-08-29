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

"""Notifications module for OpenStack Identity Service resources"""
from keystone.openstack.common import log
from keystone.openstack.common.notifier import api as notifier_api


LOG = log.getLogger(__name__)


class BaseResourceNotificationWrapper(object):
    """Decorator to send an event notification for a specific resource.

    Sends a notification if the wrapped callable does not raise an
    ``Exception``.

    :param resource_type: type of resource being affected
    :param host: host of the resource (optional)
    """
    def __init__(self, resource_type, host=None):
        self.resource_type = resource_type
        self.host = host

    def __call__(self, f):
        def wrapper(*args, **kwargs):
            """Send a notification if the wrapped callable is successful."""
            try:
                # self will be the first arg, followed by the resource ID
                resource_id = args[1]
                result = f(*args, **kwargs)
            except Exception:
                raise
            else:
                _send_notification(
                    self.operation,
                    self.resource_type,
                    resource_id,
                    self.host)
            return result

        return wrapper


class created(BaseResourceNotificationWrapper):
    """Decorator to send a created resource notification."""

    def __init__(self, *args, **kwargs):
        super(created, self).__init__(*args, **kwargs)
        self.operation = 'created'


class updated(BaseResourceNotificationWrapper):
    """Decorator to send a updated resource notification."""

    def __init__(self, *args, **kwargs):
        super(updated, self).__init__(*args, **kwargs)
        self.operation = 'updated'


class deleted(BaseResourceNotificationWrapper):
    """Decorator to send a deleted resource notification."""

    def __init__(self, *args, **kwargs):
        super(deleted, self).__init__(*args, **kwargs)
        self.operation = 'deleted'


def _send_notification(operation, resource_type, resource_id, host=None):
    """Send notification to inform observers about the affected resource.

    This method doesn't raise an exception when sending the notification fails.

    :param operation: operation being performed (created, updated, or deleted)
    :param resource_type: type of resource being operated on
    :param resource_id: ID of resource being operated on
    :param host: resource host
    """
    context = {}
    payload = {'resource_info': resource_id}
    service = 'identity'
    publisher_id = notifier_api.publisher_id(service, host=host)
    event_type = '%(service)s.%(resource_type)s.%(operation)s' % {
        'service': service,
        'resource_type': resource_type,
        'operation': operation}

    try:
        notifier_api.notify(
            context, publisher_id, event_type, notifier_api.INFO, payload)
    except Exception:
        msg = (_('Failed to send %(res_id)s %(event_type)s notification') %
               {'res_id': resource_id, 'event_type': event_type})
        LOG.exception(msg)
