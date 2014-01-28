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

import pycadf
from pycadf import cadftaxonomy as taxonomy
from pycadf import cadftype
from pycadf import eventfactory
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
        self.action = action

    def __call__(self, f):
        def wrapper(wrapped_self, context, user_id, *args, **kwargs):
            """Always send a notification."""

            remote_addr = None
            http_user_agent = None
            environment = context.get('environment')

            if environment:
                remote_addr = environment.get('REMOTE_ADDR')
                http_user_agent = environment.get('HTTP_USER_AGENT')

            host = pycadf.host.Host(address=remote_addr, agent=http_user_agent)
            initiator = resource.Resource(typeURI=taxonomy.ACCOUNT_USER,
                                          name=user_id, host=host)

            _send_audit_notification(self.action, initiator,
                                     taxonomy.OUTCOME_PENDING)
            try:
                result = f(wrapped_self, context, user_id, *args, **kwargs)
            except Exception:
                # For authentication failure send a cadf event as well
                _send_audit_notification(self.action, initiator,
                                         taxonomy.OUTCOME_FAILURE)
                raise
            else:
                _send_audit_notification(self.action, initiator,
                                         taxonomy.OUTCOME_SUCCESS)
                return result

        return wrapper


def _send_audit_notification(action, initiator, outcome):
    """Send CADF notification to inform observers about the affected resource.

    This method doesn't raise an exception when sending the notification fails.

    :param action: CADF action being audited (e.g., 'authenticate')
    :param initiator: CADF resource representing the initiator
    :param outcome: The CADF outcome (taxonomy.OUTCOME_PENDING,
        taxonomy.OUTCOME_SUCCESS, taxonomy.OUTCOME_FAILURE)

    """

    event = eventfactory.EventFactory().new_event(
        eventType=cadftype.EVENTTYPE_ACTIVITY,
        outcome=outcome,
        action=action,
        initiator=initiator,
        target=resource.Resource(typeURI=taxonomy.ACCOUNT_USER),
        observer=resource.Resource(typeURI='service/security'))

    context = {}
    payload = event.as_dict()
    LOG.debug(_('CADF Event: %s'), payload)
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

emit_event = CadfNotificationWrapper
