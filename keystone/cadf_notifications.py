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

from pycadf import cadftaxonomy as taxonomy
from pycadf import eventfactory
from pycadf import host as pycadf_host
from pycadf import resource

from keystone.openstack.common import log
from keystone.openstack.common.notifier import api as notifier_api

LOG = log.getLogger(__name__)


class CadfNotificationWrapper(object):
    """Send CADF event notifications for various methods.

    Sends CADF notifications for events such as whether an authentication was
    successful or not.
    """
    def __init__(self, action):
        self.cadf_action = action

    def __call__(self, f):
        def wrapper(wrapped_self, context, user_id, *args, **kwargs):
            """Send a notification if the wrapped callable is successful."""
            remote_addr = None
            http_user_agent = None
            environment = context.get('environment')
            if environment:
                remote_addr = environment.get('REMOTE_ADDR')
                http_user_agent = environment.get('HTTP_USER_AGENT')
            _send_audit_notification(action=self.cadf_action,
                                     remote_addr=remote_addr,
                                     http_user_agent=http_user_agent,
                                     user_id=user_id,
                                     outcome=taxonomy.OUTCOME_PENDING)
            try:
                result = f(wrapped_self, context, user_id, *args, **kwargs)
            except Exception:
                # For authentication failure send a cadf event as well
                _send_audit_notification(action=self.cadf_action,
                                         remote_addr=remote_addr,
                                         http_user_agent=http_user_agent,
                                         user_id=user_id,
                                         outcome=taxonomy.OUTCOME_FAILURE)
                raise
            else:
                _send_audit_notification(action=self.cadf_action,
                                         remote_addr=remote_addr,
                                         http_user_agent=http_user_agent,
                                         user_id=user_id,
                                         outcome=taxonomy.OUTCOME_SUCCESS)
            return result

        return wrapper


def emit_event(action):
    """Decorator to send notifications for Authenticate methods."""
    return CadfNotificationWrapper(action)


def _send_audit_notification(action, remote_addr, http_user_agent, user_id,
                             outcome):
    """Send CADF notification to inform observers about the affected resource.

    This method doesn't raise an exception when sending the notification fails.

    :param action: CADF action being audited (authenticate)
    :param remote_addr: the IP address of the client requesting authentication
    :param http_user_agent: HTTP user agent from the authentication request
    :param user_name: the user name sent in with the authentication request
    :param outcome: the CADF outcome (pending, success, failure)

    """
    initiator_host = pycadf_host.Host(address=remote_addr,
                                      agent=http_user_agent)
    initiator = resource.Resource(typeURI=taxonomy.ACCOUNT_USER,
                                  name=user_id,
                                  host=initiator_host)

    event = eventfactory.EventFactory().new_event(
        eventType='activity',
        outcome=outcome,
        action=action,
        initiator=initiator,
        target=resource.Resource(typeURI='service/security/account/user'),
        observer=resource.Resource(typeURI='service/security'))
    LOG.debug(_('Keystone CADF Event: %s'), event.as_dict())
    context = {}
    payload = event.as_dict()
    service = 'identity'
    publisher_id = notifier_api.publisher_id(service)
    event_type = '%(service)s.%(action)s' % {'service': service,
                                             'action': action}

    try:
        notifier_api.notify(
            context, publisher_id, event_type, notifier_api.INFO, payload)
    except Exception:
        LOG.exception(
            _('Failed to send %(action)s %(event_type)s notification'),
            {'action': action, 'event_type': event_type})
