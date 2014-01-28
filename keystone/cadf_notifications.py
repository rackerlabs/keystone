# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 IBM Corp.
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

""" CADF Notifications module for OpenStack Identity Service resources"""

from keystone.openstack.common import log
from keystone.openstack.common.notifier import api as notifier_api


LOG = log.getLogger(__name__)



class CadfNotificationWrapper(object):
    """Send cadf event notifications for various methods.

    Sends notifications for events such as whether an authentication was
    successful or not.
    """
    def __init__(self, action):
        self.cadf_action = action
        print("BT cadf_action = ")
        print(self.cadf_action)
        #print("BT About to print resource_type")
        #print(resource_type)


    def __call__(self, f):
        
        print("BT inside __call__")
        print(f)
        def wrapper(*args, **kwargs):
            """Send a notification if the wrapped callable is successful."""
            try:
                print("CADF ABout to call f")
                result = f(*args, **kwargs)
            except Exception:
                # For authentication failure send a cadf event as well
                print("CADF Send Authentication Failed")
                _send_notification(self.cadf_action)
                raise
            else:
                print ("CADF Send Authentication Succeeded")
                _send_notification(self.cadf_action)
                #_send_notification(
                #    self.operation,
                #    self.resource_type,
                #    args[1],  # f(self, resource_id, ...)
                #    self.host)
            return result

        return wrapper


def emit_cadf_event(*args, **kwargs):
    """Decorator to send notifications for Authenticate methods."""
    print("BTBTBT authenticate has been called")
    print(args)
    return CadfNotificationWrapper(*args, **kwargs)


def _send_notification(action):
    """Send CADF notification to inform observers about the affected resource.

    This method doesn't raise an exception when sending the notification fails.


    """
    print("_send_notification called")
    #context = {}
    #payload = {'resource_info': resource_id}
    #service = 'identity'
    #publisher_id = notifier_api.publisher_id(service, host=host)
    #event_type = '%(service)s.%(resource_type)s.%(operation)s' % {
    #    'service': service,
    #    'resource_type': resource_type,
    #    'operation': operation}

    #try:
    #    notifier_api.notify(
    #        context, publisher_id, event_type, notifier_api.INFO, payload)
    #except Exception:
    #    LOG.exception(
    #        _('Failed to send %(res_id)s %(event_type)s notification'),
    #        {'res_id': resource_id, 'event_type': event_type})
