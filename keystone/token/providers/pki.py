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

from keystone.common import cms
from keystone.common import environment
from keystone import config
from keystone import exception
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log
from keystone.token import provider
from keystone.token.providers import common


CONF = config.CONF

LOG = log.getLogger(__name__)


class Provider(common.BaseProvider):
    def _get_token_id(self, token_data):
        try:
            token_id = cms.cms_sign_token(jsonutils.dumps(token_data),
                                          CONF.signing.certfile,
                                          CONF.signing.keyfile)
            return token_id
        except environment.subprocess.CalledProcessError:
            LOG.exception(_('Unable to sign token'))
            raise exception.UnexpectedError(_(
                'Unable to sign token.'))

    def _cms_verify_token(self, signed_data):
        formatted = cms.cms_to_token(signed_data)
        try:
            return jsonutils.loads(cms.cms_verify(formatted,
                                                  CONF.signing.certfile,
                                                  CONF.signing.ca_certs))
        except environment.subprocess.CalledProcessError:
            msg = _('Unable to verify signed token.')
            LOG.exception(msg)
            raise exception.UnexpectedError(msg)

    def validate_token(self, token_id):
        if cms.is_ans1_token(token_id):
            return self._cms_verify_token(token_id)
        return super(Provider, self).validate_token(token_id)

    def validate_v3_token(self, token_id):
        if cms.is_ans1_token(token_id):
            token_data = self._cms_verify_token(token_id)
            if self.get_token_version(token_data) == provider.V2:
                token_data = self._validate_v3_token_ref(token_data)
        else:
            token_data = super(Provider, self).validate_v2_token(token_id)
        return token_data

    def validate_v2_token(self, token_id):
        if cms.is_ans1_token(token_id):
            token_data = self._cms_verify_token(token_id)
            if self.get_token_version(token_data) == provider.V3:
                token_data = self._validate_v2_token_ref(token_data)
        else:
            token_data = super(Provider, self).validate_v2_token(token_id)
        return token_data
