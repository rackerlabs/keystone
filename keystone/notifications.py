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

"""Functionality for notifications in OpenStack Identity Service"""

from keystone.openstack.common import log as logging
from keystone.openstack.common.notifier import api as notifier_api

LOG = logging.getLogger(__name__)


def send_update(old_res, new_res, resource, host=None):
    """Send a notification update for a given resource in Keystone.

    :param old_res: resource being updated or deleted
    :param new_res: resource being updated or created
    :param resource: type of resource being modified
    :param host: resource host
    :raises Exception: if the request to send the notification fails
    """

    if old_res is None:
        event_type = ('identity.%(resource)s.created' % resource)
        res = new_res
    elif new_res is None:
        event_type = ('identity.%(resource)s.deleted' % resource)
        res = old_res
    else:
        event_type = ('identity.%(resource)s.updated' % resource)
        res = new_res

    try:
        _send_update_notification(res, event_type, host=host)
    except Exception:
        LOG.exception(_("Failed to send resource notification"))


def _send_update_notification(resource, event_type, service="identity",
                              host=None):
    """Send resource update notification to inform observers about resource
       changes.
    :param resource: resource information
    :param event_type: information about the resource being created, updated,
                       or deleted
    :param service: service owning the resouce being modified, Keystone in
                    this case
    :param host: resource host
    """

    # NOTE(ldbragst): the notifier API from Oslo requires a context be passed
    # into the notifier. In Keystone, we don't always have a context available
    # to pass in, so here we define an empty dictionary as a context to pass.
    # This also allows notifications to be implemented in the Manager classes
    # where there might not be a context.
    context = {}
    payload = {"resource_info": resource}

    publisher_id = notifier_api.publisher_id(service, host)
    notifier_api.notify(context, publisher_id, event_type,
                        notifier_api.INFO, payload)
