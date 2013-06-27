# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

from keystone.common import logging
from keystone.token.backends import fake

LOG = logging.getLogger(__name__)


class Token(fake.Token):
    """kvs backend for tokens is deprecated.

    Deprecated in Havana and renamed to keystone.tokens.backends.fake, as
    this backend should only be used for testing and not production.
    """

    # Public interface
    def get_token(self, token_id):
        LOG.warn(_("kvs token backend is deprecated use"
                   "keystone.token.backends.fake instead."))
        return super(Token, self).get_token(token_id)
