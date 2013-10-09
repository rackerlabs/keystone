# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Keystone PKI Token Provider"""

import json

from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging
from keystone.token.providers import uuid
from keystoneclient.common import cms
#from keystone.common import cms


CONF = config.CONF

LOG = logging.getLogger(__name__)

subprocess = None


# FIXME(jeffrey4l): remove this when keystoneclient import
# subprocess graceful
# When running the unittest, the subprocess imported in this
# And keystoneclient are different.
def _ensure_subprocess():
    global subprocess
    if not subprocess:
        try:
            from eventlet import patcher
            if patcher.already_patched.get('os'):
                from eventlet.green import subprocess
            else:
                import subprocess
        except ImportError:
            import subprocess  # noqa


class Provider(uuid.Provider):
    def _get_token_id(self, token_data):
        try:
            _ensure_subprocess()
            token_id = cms.cms_sign_token(json.dumps(token_data),
                                          CONF.signing.certfile,
                                          CONF.signing.keyfile)
            return token_id
        except subprocess.CalledProcessError:
            LOG.exception('Unable to sign token')
            raise exception.UnexpectedError(_(
                'Unable to sign token.'))
