# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 IBM Corp.
# All Rights Reserved
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

from keystone.openstack.common.notifier import api as notifier_api

notify_opts = []


def send_update(context, old_res, new_res, service="identity", host=None):
    """Send a notification update for a given resource in Keystone"""

    if old_res is None:
        event_type = 'identity.resource.created'
        resource = new_res
    elif new_res is None:
        event_type = 'identity.resource.deleted'
        resource = old_res
    else:
        event_type = 'identity.resource.updated'
        resource = new_res

    try:
        _send_update_notification(context, resource, event_type,
                                  service=service, host=host)
    except Exception:
        LOG.exception(_("Failed to send resource notification"))

def _send_update_notification(context, resource, event_type,
                service="identity", host=None):
    """Send resource update notification to inform observers about resource
    changes"""

    # NOTE(ldbragst): Grab extra information about resource here if
    #                 needed/possible

    # NOTE(ldbragst): build payload
    payload["resource_info"] = resource

    publisher_id = notifier_api.publisher_id(service, host)
    notifier_api.notify(context, publisher_id, event_type,
                        notifier_api.INFO, payload)

