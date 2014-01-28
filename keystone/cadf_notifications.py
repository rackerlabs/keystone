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
#TODO(topol) Turn on notification in subsequent patch set
#from keystone.openstack.common.notifier import api as notifier_api

from pycadf import cadftaxonomy as taxonomy
from pycadf import eventfactory
from pycadf import host
from pycadf import identifier
from pycadf import resource


LOG = log.getLogger(__name__)


class CadfNotificationWrapper(object):
    """Send cadf event notifications for various methods.

    Sends notifications for events such as whether an authentication was
    successful or not.
    """
    def __init__(self, action):
        self.cadf_action = action

    def __call__(self, f):

        def wrapper(*args, **kwargs):
            remote_addr = None
            http_user_agent = None
            user_name = None
            """Send a notification if the wrapped callable is successful."""
            environment = args[1].get('environment', None)
            if environment:
                remote_addr = environment.get('REMOTE_ADDR', None)
                http_user_agent = environment.get('HTTP_USER_AGENT', None)
            auth = args[1].get('environment', None)
            if auth:
                try:
                    user_name = auth['identity']['password']['user']['name']
                except KeyError:
                    user_name = None
            try:
                _send_notification(action=self.cadf_action,
                                   remote_addr=remote_addr,
                                   http_user_agent=http_user_agent,
                                   user_name=user_name,
                                   outcome='pending')
                result = f(*args, **kwargs)
            except Exception:
                # For authentication failure send a cadf event as well
                _send_notification(action=self.cadf_action,
                                   remote_addr=remote_addr,
                                   http_user_agent=http_user_agent,
                                   user_name=user_name,
                                   outcome='failure')
                raise
            else:
                _send_notification(action=self.cadf_action,
                                   remote_addr=remote_addr,
                                   http_user_agent=http_user_agent,
                                   user_name=user_name,
                                   outcome='success')
            return result

        return wrapper


def emit_event(*args, **kwargs):
    """Decorator to send notifications for Authenticate methods."""
    return CadfNotificationWrapper(*args, **kwargs)


def _send_notification(action, remote_addr, http_user_agent, user_name,
                       outcome):
    """Send CADF notification to inform observers about the affected resource.

    This method doesn't raise an exception when sending the notification fails.


    """
    initiator_host = host.Host(address=remote_addr, agent=http_user_agent)
    initiator = resource.Resource(typeURI=taxonomy.ACCOUNT_USER,
                                  name=user_name,
                                  host=initiator_host)

    event = eventfactory.EventFactory().new_event(
        eventType='activity',
        outcome=outcome,
        action=action,
        initiator=initiator,
        target=resource.Resource(typeURI='service/security/account/user'),
        targetId=identifier.generate_uuid())
    LOG.debug(_('Keystone CADF Event: %s'), event.as_dict)
    #print((event.as_dict()))
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
