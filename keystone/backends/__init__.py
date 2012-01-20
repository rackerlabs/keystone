# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 OpenStack LLC.
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

# pylint: disable=W0603
import ast
import logging

from keystone.cfg import NoSuchOptError
from keystone import config
from keystone import utils

logger = logging.getLogger(__name__)  # pylint: disable=C0103

CONF = config.CONF
DEFAULT_BACKENDS = "keystone:backends:sqlalchemy"

#Configs applicable to all backends.
SHOULD_HASH_PASSWORD = CONF.hash_password


class GroupConf(CONF.__class__):
    """ Allows direct access to the values in the backend groups."""
    def __init__(self, group, *args, **kwargs):
        self.group = group
        super(GroupConf, self).__init__(*args, **kwargs)

    def __getattr__(self, att):
        try:
            return CONF._get(att, self.group)
        except NoSuchOptError:
            return None


def configure_backends():
    """Load backends given in the 'backends' option."""
    backend_names = CONF.backends or DEFAULT_BACKENDS
    # Old configs may still have backend names with periods instead
    # of colon separators
    if "." in backend_names:
        # TODO(ziad): verify if that is what other projects are moving
        # to? If so, make this a warning
        logger.debug("Your configuration may be out-of-date and using "\
                "an old format for the 'backends' setting. The value '%s' "\
                "should use colons instead of periods.\n\n" % backend_names)
        backend_names = backend_names.replace(".", ":")
    for backend in backend_names.split(","):
        # Config groups are separated with colons; change to
        # periods for importing.
        module_name = backend.replace(":", ".")
        backend_module = utils.import_module(module_name)
        backend_conf = GroupConf(backend)
        backend_module.configure_backend(backend_conf)
