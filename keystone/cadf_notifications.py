# vim: tabstop=4 shiftwidth=4 softtabstop=4
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

        def wrapper(*args, **kwargs):
            """Send a notification if the wrapped callable is successful."""
            context = args[1]
            remote_addr = None
            http_user_agent = None
            auth_identifier = None
            environment = context.get('environment')
            if environment:
                remote_addr = environment.get('REMOTE_ADDR')
                http_user_agent = environment.get('HTTP_USER_AGENT')
                openstack_params = environment.get('openstack.params')
                if openstack_params:
                    auth = openstack_params.get('auth')
                    if auth:
                        auth_identifier = _get_identifier_from_auth(auth)
            _send_audit_notification(action=self.cadf_action,
                                     remote_addr=remote_addr,
                                     http_user_agent=http_user_agent,
                                     user_name=auth_identifier,
                                     outcome=taxonomy.OUTCOME_PENDING)
            try:
                result = f(*args, **kwargs)
            except Exception:
                # For authentication failure send a cadf event as well
                _send_audit_notification(action=self.cadf_action,
                                         remote_addr=remote_addr,
                                         http_user_agent=http_user_agent,
                                         user_name=auth_identifier,
                                         outcome=taxonomy.OUTCOME_FAILURE)
                raise
            else:
                _send_audit_notification(action=self.cadf_action,
                                         remote_addr=remote_addr,
                                         http_user_agent=http_user_agent,
                                         user_name=auth_identifier,
                                         outcome=taxonomy.OUTCOME_SUCCESS)
            return result

        return wrapper


def emit_event(*args, **kwargs):
    """Decorator to send notifications for Authenticate methods."""
    return CadfNotificationWrapper(*args, **kwargs)


def _lookup(dic, key, *keys):
    if keys:
        return _lookup(dic.get(key, {}), *keys)
    return dic.get(key)


def _get_identifier_from_auth(auth):
    """Try and get some form of auth identifier

    Auth identifier could be a username plus domain name or domain id
    or it could be a user_id

    """
    user_name = None
    user_id = None
    domain_name = None
    # First try V2 auth structure.
    if 'passwordCredentials' in auth:
        user_name = _lookup(auth, 'passwordCredentials', 'username')
        if user_name:
            #For V2 username is all we need
            return user_name
        else:
            #If no username check for user_id
            user_id = _lookup(auth, 'passwordCredentials', 'userId')
            if user_id:
                return user_id
        #If we get here just return user_name even if None
        return user_name
    #  Otherwise see if we have a V3 auth structure
    elif 'identity' in auth:
        #Check if a user_id exists
        user_id = _lookup(auth, 'identity', 'password', 'user', 'id')
        if user_id:
            #if user_id exists that is all we need. We are done
            return user_id
        else:
            #Check for a username
            user_name = _lookup(auth, 'identity', 'password', 'user', 'name')
            if user_name:
                #Need a domain name or a domain id when using user_name
                domain_name = _lookup(auth, 'identity', 'password', 'user',
                                      'domain', 'name')
                if domain_name:
                    #If we have user_name and domain_name we are done
                    return user_name + '@' + domain_name
                else:
                    domain_id = _lookup(auth, 'identity', 'password', 'user',
                                        'domain', 'id')
                    if domain_id:
                        #If we have user_name and domain_id we are done
                        return user_name + '@' + domain_id
    # If we get this far just return user_name even if None
    LOG.debug(_('No v2 or v3 auth structure was detected'))
    return user_name


def _send_audit_notification(action, remote_addr, http_user_agent, user_name,
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
                                  name=user_name,
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
