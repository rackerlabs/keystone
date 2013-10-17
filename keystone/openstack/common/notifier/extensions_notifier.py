# Copyright 2011 OpenStack Foundation.
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


from oslo.config import cfg

from keystone.openstack.common import context as req_context
from keystone.openstack.common import importutils
from keystone.openstack.common.gettextutils import _  # noqa
from keystone.openstack.common import log as logging
from keystone.openstack.common import rpc

LOG = logging.getLogger(__name__)

notification_topic_opt = cfg.ListOpt(
    'notification_topics', default=['notifications', ],
    help='topic used for OpenStack notifications')
extension_notifications_opt = cfg.ListOpt(
    'extensions', default=[],
    help='list of extensions to notify')

CONF = cfg.CONF
CONF.register_opt(notification_topic_opt)
CONF.register_opt(extension_notifications_opt,
                  group='extension_notifications')

subscribers = {}
#extensions = []

#for extension in CONF.extension_notifications.extensions:
#    current_extension = importutils.import_object(extension)
#    subscriptions = current_extension.subscriptions()
#    for subscription_event, subscription_callback in subscriptions.iteritems():
#        if subscription_event not in subscribers:
#            subscribers.update({ subscription_event: { 'subscribers': [] } })
#        subscribers[subscription_event]['subscribers'].append(
#            getattr(current_extension, subscription_callback))

def register(subscriptions):
    global subscribers
    print '*************** WTF **************'
    for subscription_event, subscription_callback in subscriptions.iteritems():
        subscribers.setdefault(subscription_event, { 'subscribers': [] })
        subscribers[subscription_event]['subscribers'].append(subscription_callback)


def notify(context, message):
    """Sends a notification via RPC."""
    if not context:
        context = req_context.get_admin_context()
    priority = message.get('priority',
                           CONF.default_notification_level)
    priority = priority.lower()
    event = message.get('event_type')
    print '***********************'+event
    print '------- %s' % subscribers.keys()
    for extension in subscribers[event]['subscribers']:
        extension(context, message)
