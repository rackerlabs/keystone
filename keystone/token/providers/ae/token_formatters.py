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

import datetime

from keyczar import keyczar
import msgpack
from oslo.utils import timeutils

from keystone import config
from keystone import exception
from keystone.openstack.common import log

CONF = config.CONF
LOG = log.getLogger(__name__)


class BaseTokenFormatter(object):
    """Base object for token formatters to inherit."""

    # NOTE(lbragstad): Each class the inherits BaseTokenFormatter should define
    # the `token_format` and `token_version`. The combination of the two should
    # create a unique combination.
    token_format = None
    token_version = None

    def __init__(self):
        """Establish a connection with Keyczar and store it."""
        self.key_repository = CONF.ae_tokens.key_repository
        try:
            self.crypter = keyczar.Crypter.Read(self.key_repository)
        except keyczar.errors.KeyczarError as e:
            raise exception.UnexpectedError(e)


# FIXME(lbragstad): WTF is a "standard token". Come up with a better naming
# convention for these!
class StandardTokenFormatter(BaseTokenFormatter):

    token_format = 'AE'
    token_version = '01'

    def __init__(self):
        super(StandardTokenFormatter, self).__init__()

    def create_token(self, user_id, project_id, issued_at, expires_at,
            audit_ids):
        """Create a standard formatted token.

        :param user_id: ID of the user in the token request
        :param project_id: ID of the project to scope to
        :param issued_at: timestamp integer of the creation time
        :param expires_at: timestamp integer of the expiration time
        :param audit_ids: audit IDs
        :returns: a string representing the token

        """

        if isinstance(audit_ids, list) and len(audit_ids) == 1:
            audit_ids = audit_ids.pop()

        token = [user_id, project_id, issued_at, expires_at, audit_ids]
        msgpacked_token = msgpack.packb(token)

        # NOTE(lbragstad): Now we're ready to pass our compressed token
        # information to Keyczar since Keyczar will handle the encryption and
        # digest stuff.
        encrypted_token = self.crypter.Encrypt(msgpacked_token)
        return encrypted_token

    def validate_token():
        pass
