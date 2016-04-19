# Copyright 2016 Morgan Fainberg
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

import uuid

from oslo_log import log
from oslo_utils import timeutils

from keystone.common import sql
from keystone import exception
from keystone.i18n import _LW
from keystone.token.providers import fernet
from keystone.token.providers.fernet.uuid_msgpack import persistence


LOG = log.getLogger(__name__)


class UUIDMsgPack(fernet.Provider):
    """A Token Provider which stores Fernet payloads in the DB."""

    def __init__(self, *args, **kwargs):
        super(UUIDMsgPack, self).__init__(*args, **kwargs)
        # NOTE(morganfainberg): Override the token formatter's pack, unpack,
        # and creation_time methods with ones that will back to the explicit
        # persistence as expected.
        self.token_formatter.pack = self._pack
        self.token_formatter.unpack = self._unpack
        self.token_formatter.creation_time = self._creation_time
        LOG.warning(_LW('Running Keystone with the UUIDMsgPack Token Provider.'
                        'It is highly recommended that keystone is run using '
                        'the Fernet provider instead as there is no '
                        'persistence requirement for the token data.'))

    @classmethod
    def _pack(cls, payload):
        """This method replaces the token_formatter pack() method."""
        token_id = uuid.uuid4().int
        create_time = timeutils.utcnow_ts(microsecond=False)
        token_ref = persistence.UUIDMsgPackModel()
        token_ref.creation_time = create_time
        token_ref.id = token_id
        token_ref.payload = payload
        with sql.session_for_write() as session:
            session.add(token_ref)
        return token_id

    @classmethod
    def _unpack(cls, token):
        """This method replaces the token_formatter unpack() method."""
        with sql.session_for_read() as session:
            token_ref = session.query(persistence.UUIDMsgPackModel).get(token)
            if not token_ref:
                raise exception.TokenNotFound(token_id=token)
            return token_ref.payload

    @classmethod
    def _creation_time(cls, token):
        """This method replaces the token_formatter creation_time() method."""
        with sql.session_for_read() as session:
            creation_time = session.query(
                persistence.UUIDMsgPackModel.creation_time).get(token)
            if not creation_time:
                raise exception.TokenNotFound(token_id=token)
            return creation_time
