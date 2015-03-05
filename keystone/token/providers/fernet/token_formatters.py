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

import uuid

from cryptography import fernet
from oslo_config import cfg
from oslo_log import log
import six

from keystone import exception
from keystone.token.providers.fernet import utils


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class TokenFormatter(object):
    """Packs and unpacks payloads into tokens for transport."""

    @property
    def crypto(self):
        """Return a cryptography instance.

        You can extend this class with a custom crypto @property to provide
        your own token encoding / decoding. For example, using a different
        cryptography library (e.g. ``python-keyczar``) or to meet arbitrary
        security requirements.

        This @property just needs to return an object that implements
        ``encrypt(plaintext)`` and ``decrypt(ciphertext)``.

        """
        keys = utils.load_keys()

        if not keys:
            raise exception.KeysNotFound()

        fernet_instances = [fernet.Fernet(key) for key in utils.load_keys()]
        return fernet.MultiFernet(fernet_instances)

    def pack(self, payload):
        """Pack a payload for transport as a token."""
        return self.crypto.encrypt(payload)

    def unpack(self, token):
        """Unpack a token, and validate the payload."""
        try:
            return self.crypto.decrypt(token, ttl=CONF.token.expiration)
        except fernet.InvalidToken as e:
            raise exception.Unauthorized(six.text_type(e))


class BasePayload(object):
    # each payload variant should have a unique version
    version = None

    @classmethod
    def assemble(cls, *args):
        """Assemble the payload of an unscoped token.

        :param args: whatever data should go into the payload
        :returns: the payload of an unscoped token

        """
        raise NotImplementedError()

    @classmethod
    def disassemble(cls, payload):
        """Disassemble an unscoped payload into the component data.

        :param payload: this variant of payload
        :returns: a tuple of the payloads component data

        """
        raise NotImplementedError()

    @classmethod
    def convert_uuid_hex_to_bytes(cls, uuid_string):
        """Compress UUID formatted strings to bytes.

        :param uuid_string: uuid string to compress to bytes
        :returns: a byte representation of the uuid

        """
        # TODO(lbragstad): Wrap this in an exception. Not sure what the case
        # would be where we couldn't handle what we've been given but incase
        # the integrity of the token has been compromised.
        uuid_obj = uuid.UUID(uuid_string)
        return uuid_obj.bytes

    @classmethod
    def convert_uuid_bytes_to_hex(cls, uuid_byte_string):
        """Generate uuid.hex format based on byte string.

        :param uuid_byte_string: uuid string to generate from
        :returns: uuid hex formatted string

        """
        # TODO(lbragstad): Wrap this in an exception. Not sure what the case
        # would be where we couldn't handle what we've been given but incase
        # the integrity of the token has been compromised.
        uuid_obj = uuid.UUID(bytes=uuid_byte_string)
        return uuid_obj.hex


class UnscopedPayload(BasePayload):
    version = 0

    @classmethod
    def assemble(cls, user_id, audit_ids):
        """Assemble the payload of an unscoped token.

        :param user_id: identifier of the user in the token request
        :param audit_ids: list of the token's audit IDs
        :returns: the payload of an unscoped token

        """
        b_user_id = cls.convert_uuid_hex_to_bytes(user_id)
        return (b_user_id, audit_ids)

    @classmethod
    def disassemble(cls, payload):
        """Disassemble an unscoped payload into the component data.

        :param payload: the payload of an unscoped token
        :return: a tuple containing the user_id and audit_ids

        """
        user_id = cls.convert_uuid_bytes_to_hex(payload[0])
        audit_ids = payload[1]

        return (user_id, audit_ids)


class DomainScopedPayload(BasePayload):
    version = 1

    @classmethod
    def assemble(cls, user_id, domain_id, audit_ids):
        """Assemble the payload of a domain-scoped token.

        :param user_id: ID of the user in the token request
        :param project_id: ID of the project to scope to
        :param audit_ids: list of the token's audit IDs
        :returns: the payload of a domain-scoped token

        """
        b_user_id = cls.convert_uuid_hex_to_bytes(user_id)
        try:
            b_domain_id = cls.convert_uuid_hex_to_bytes(domain_id)
        except ValueError:
            # the default domain ID is configurable, and probably isn't a UUID
            if domain_id == CONF.identity.default_domain_id:
                b_domain_id = domain_id
            else:
                raise
        return (b_user_id, b_domain_id, audit_ids)

    @classmethod
    def disassemble(cls, payload):
        """Disassemble a payload into the component data.

        :param payload: the payload of a token
        :return: a tuple containing the user_id, project_id and audit_ids

        """
        user_id = cls.convert_uuid_bytes_to_hex(payload[0])
        try:
            domain_id = cls.convert_uuid_bytes_to_hex(payload[1])
        except ValueError:
            # the default domain ID is configurable, and probably isn't a UUID
            if payload[1] == CONF.identity.default_domain_id:
                domain_id = payload[1]
            else:
                raise
        audit_ids = payload[2]

        return (user_id, domain_id, audit_ids)


class ProjectScopedPayload(BasePayload):
    version = 2

    @classmethod
    def assemble(cls, user_id, project_id, audit_ids):
        """Assemble the payload of a project-scoped token.

        :param user_id: ID of the user in the token request
        :param project_id: ID of the project to scope to
        :param audit_ids: list of the token's audit IDs
        :returns: the payload of a project-scoped token

        """
        b_user_id = cls.convert_uuid_hex_to_bytes(user_id)
        b_scope_id = cls.convert_uuid_hex_to_bytes(project_id)
        return (b_user_id, b_scope_id, audit_ids)

    @classmethod
    def disassemble(cls, payload):
        """Disassemble a payload into the component data.

        :param payload: the payload of a token
        :return: a tuple containing the user_id, project_id and audit_ids

        """
        user_id = cls.convert_uuid_bytes_to_hex(payload[0])
        project_id = cls.convert_uuid_bytes_to_hex(payload[1])
        audit_ids = payload[2]

        return (user_id, project_id, audit_ids)


class TrustScopedPayload(BasePayload):
    version = 3

    @classmethod
    def assemble(cls, user_id, project_id, audit_ids, trust_id):
        """Assemble the payload of a trust-scoped token.

        :param user_id: ID of the user in the token request
        :param project_id: ID of the project to scope to
        :param audit_ids: list of the token's audit IDs
        :param trust_id: ID of the trust in effect
        :returns: the payload of a trust-scoped token

        """
        b_user_id = cls.convert_uuid_hex_to_bytes(user_id)
        b_project_id = cls.convert_uuid_hex_to_bytes(project_id)
        b_trust_id = cls.convert_uuid_hex_to_bytes(trust_id)

        return (b_user_id, b_project_id, b_trust_id, audit_ids)

    @classmethod
    def disassemble(cls, payload):
        """Validate a trust-based payload.

        :param token_string: a string representing the token
        :returns: a tuple containing the user_id, project_id, audit_ids, and
                  trust_id

        """
        user_id = cls.convert_uuid_bytes_to_hex(payload[0])
        project_id = cls.convert_uuid_bytes_to_hex(payload[1])
        trust_id = cls.convert_uuid_bytes_to_hex(payload[2])
        audit_ids = payload[3]

        return (user_id, project_id, audit_ids, trust_id)
