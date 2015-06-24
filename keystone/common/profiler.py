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

import logging

import osprofiler.notifier
import oslo_messaging

from keystone import config
from keystone import notifications


CONF = config.CONF
LOG = logging.getLogger(__name__)


def setup(name, host='0.0.0.0'):

    if CONF.profiler.enabled:
        _notifier = osprofiler.notifier.create(
            "Messaging", oslo_messaging, {},
            notifications.get_transport(), "keystone", name, host)
        osprofiler.notifier.set(_notifier)
        LOG.info("OSProfiler is enabled.\nIt means that person who knows "
                 "any of hmac_keys that are specified in "
                 "/etc/keystone-paste.ini can trace his requests. \n"
                 "In real life only operator can read this file so there "
                 "is no security issue. Note that even if person can "
                 "trigger profiler, only admin user can retrieve trace "
                 "information.\n"
                 "To disable OSprofiler set in keystone.conf:\n"
                 "[profiler]\nenabled=false")
