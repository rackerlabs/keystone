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


def notify_created(resource_id, resource_type, host=None):
    """Send resource creation notification.

    :param resource_id: ID of the resource being created
    :param resource_type: type of resource being created
    :param host: host of the resource
    """

    event_type = ('identity.%(resource_type)s.created' %
                  {'resource_type': resource_type})
    _send_notification(resource_id, event_type, host=host)


def notify_updated(resource_id, resource_type, host=None):
    """Send resource update notification.

    :param resource_id: ID of the resource being updated
    :param resource_type: type of resource being updated
    :param host: host of the resource
    """

    event_type = ('identity.%(resource_type)s.updated' %
                  {'resource_type': resource_type})
    _send_notification(resource_id, event_type, host=host)


def notify_deleted(resource_id, resource_type, host=None):
    """Send resource deletion notification.

    :param resource_id: ID of the resource being deleted
    :param resource_type: type of resource being deleted
    :param host: host of the resource
    """

    event_type = ('identity.%(resource_type)s.deleted' %
                  {'resource_type': resource_type})
    _send_notification(resource_id, event_type, host=host)


def _send_notification(resource_id, event_type, host=None):
    """Send resource update notification to inform observers about resource
       changes.

    :param resource_id: ID of resource in notification
    :param event_type: information about the resource being created, updated,
                       or deleted
    :param host: resource host
    """

    # NOTE(ldbragst): the notifier API from Oslo requires a context be passed
    # into the notifier. In Keystone, we don't always have a context available
    # to pass in, so here we define an empty dictionary as a context to pass.
    # This also allows notifications to be implemented in the Manager classes
    # where there might not be a context.
    context = {}
    payload = {'resource_info': resource_id}
    service = 'identity'
    publisher_id = notifier_api.publisher_id(service, host)

    try:
        notifier_api.notify(context, publisher_id, event_type,
                            notifier_api.INFO, payload)
    except Exception:
        msg = (_('Failed to send %(res_id)s %(event_type)s notification') %
               {'res_id': resource_id, 'event_type': event_type})
        LOG.exception(msg)
