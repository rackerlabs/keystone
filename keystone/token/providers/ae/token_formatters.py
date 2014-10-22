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
import uuid

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

    def _convert_uuid_hex_to_bytes(self, uuid_string):
        """Compress UUID formatted strings to bytes.

        :param uuid_string: uuid string to compress to bytes
        :returns: a byte representation of the uuid

        """
        # TODO(lbragstad): Wrap this in an exception. Not sure what the case
        # would be where we couldn't handle what we've been given but incase
        # the integrity of the token has been compromised.
        uuid_obj = uuid.UUID('{' + uuid_string + '}')
        return uuid_obj.bytes

    def _convert_uuid_bytes_to_hex(self, uuid_byte_string):
        """Generate uuid.hex format based on byte string.

        :param uuid_byte_string: uuid string to generate from
        :return: uuid hex formatted string

        """
        # TODO(lbragstad): Wrap this in an exception. Not sure what the case
        # would be where we couldn't handle what we've been given but incase
        # the integrity of the token has been compromised.
        uuid_obj = uuid.UUID(bytes=uuid_byte_string)
        return uuid_obj.hex


    def _convert_time_string_to_int(self, time_string):
        """Convert a time formatted string to a timestamp integer.

        :param time_string: time formatted string
        :returns: an integer timestamp

        """
        time_object = timeutils.parse_isotime(time_string)
        return int(time_object.strftime('%s'))

    def _convert_int_to_time_string(self, time_int):
        """Convert a timestamp integer to a string.

        :param time_int: integer representing time
        :returns: a time formatted string

        """
        time_object = datetime.datetime.fromtimestamp(int(time_int))
        #return timeutils.strtime(at=time_object)
        return timeutils.isotime(time_object, subsecond=True)


# FIXME(lbragstad): WTF is a "standard token". Come up with a better naming
# convention for these!
class StandardTokenFormatter(BaseTokenFormatter):

    token_format = 'AE01'

    def __init__(self):
        super(StandardTokenFormatter, self).__init__()

    def create_token(self, user_id, project_id, token_data):
        """Create a standard formatted token.

        :param user_id: ID of the user in the token request
        :param project_id: ID of the project to scope to
        :param token_data: dictionary of token data
        :returns: a string representing the token

        """
        created_at = token_data['token']['issued_at']
        issued_at_int = self._convert_time_string_to_int(created_at)
        expires_at = token_data['token']['expires_at']
        expires_at_int = self._convert_time_string_to_int(expires_at)
        audit_ids = token_data['token']['audit_ids']

        if isinstance(audit_ids, list) and len(audit_ids) == 1:
            audit_ids = audit_ids.pop()

        b_user_id = self._convert_uuid_hex_to_bytes(user_id)
        if project_id:
            b_project_id = self._convert_uuid_hex_to_bytes(project_id)
            token = [b_user_id, b_project_id, issued_at_int, expires_at_int,
                    audit_ids]
        else:
            token = [b_user_id, issued_at_int, expires_at_int, audit_ids]

        msgpacked_token = msgpack.packb(token)

        # NOTE(lbragstad): Now we're ready to pass our compressed token
        # information to Keyczar since Keyczar will handle the encryption and
        # digest stuff.
        encrypted_token = self.crypter.Encrypt(msgpacked_token)

        # Tack the token format on to the encrypted_token
        token_id = self.token_format + encrypted_token
        return token_id

    def validate_token(self, token_string):
        """Validate an AE01 formatted token.

        :param token_string: a string representing the token
        :return: a dictionary of token data

        """
        # TODO(lbragstad): catch keyczar errors here
        decrypted_token = self.crypter.Decrypt(token_string)

        # TODO(lbragstad): catch msgpack errors here
        unpacked_token = msgpack.unpackb(decrypted_token)

        # Pull out all information we need
        b_user_id = unpacked_token[0]
        b_project_id = None
        if isinstance(unpacked_token[1], str):
            b_project_id = unpacked_token[1]
            issued_at_ts = unpacked_token[2]
            expires_at_ts = unpacked_token[3]
            audit_ids = unpacked_token[4]
        else:
            issued_at_ts = unpacked_token[1]
            expires_at_ts = unpacked_token[2]
            audit_ids = unpacked_token[3]

        # Uncompress the IDs
        user_id = self._convert_uuid_bytes_to_hex(b_user_id)
        project_id = None
        if b_project_id:
            project_id = self._convert_uuid_bytes_to_hex(b_project_id)

        # Generate created at and expires at times
        issued_at_str = self._convert_int_to_time_string(issued_at_ts)
        expires_at_str = self._convert_int_to_time_string(expires_at_ts)
        token_data = {'token': {}}
        token_data['token']['issued_at'] = issued_at_str
        token_data['token']['expires_at'] = expires_at_str
        token_data['token']['audit_ids'] = audit_ids
        # TODO(lbragstad): Check if token is revoked
        # TODO(lbragstad): Check that the user exists
        # TODO(lbragstad): Check the user scope

        return (user_id, project_id, token_data)
