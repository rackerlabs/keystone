# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

"""PKI Token Provider"""

import json
import subprocess

from keystone.common import cms
from keystone.common import logging
from keystone import config
from keystone import exception
from keystone.token_management.providers import uuid_token


CONF = config.CONF

LOG = logging.getLogger(__name__)


class PkiToken(uuid_token.UuidToken):
    def __init__(self, *args, **kwargs):
        super(PkiToken, self).__init__(*args, **kwargs)

    def _get_token_id(self, token_data):
        try:
            token_id = cms.cms_sign_token(json.dumps(token_data),
                                          CONF.signing.certfile,
                                          CONF.signing.keyfile)
            return token_id
        except subprocess.CalledProcessError:
            raise exception.UnexpectedError(_(
                'Unable to sign token.'))

    def _verify_token(self, token_ref, belongs_to=None):
        if cms.is_ans1_token(token_ref['id']):
            cms.cms_verify(cms.token_to_cms(token_ref['id']),
                           CONF.signing.certfile,
                           CONF.signing.ca_certs)
        super(PkiToken, self)._verify_token(token_ref, belongs_to)
