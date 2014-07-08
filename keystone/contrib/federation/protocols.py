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

"""Federation Protocols."""

import abc

from keystone.common import config

CONF = config.CONF


class ProtocolHandlerBase(object):
    """Base class for protocol handling plugins.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        "Initialise protocol handler"

    @abc.abstractmethod
    def get_assertion_data(self, context, auth_payload):
        """Extract assertion data in a relevant way for the protocol
        used. Returned assertion data MUST contain at least a unique
        user_id

        :param context: A dictionary with string keys and simple types as
                     values containing contextual data about the session.
        :param auth_payload: A dictionary containing client provided
        authentication data.
        :returns: A dictionary containing assertion data.
            Example assertion data:
                {
                    "user_id": "xxx@xxx",
                    "asserted_attribute_type1": "value1",
                    "asserted_attribute_type2": "value2"
                }
            Example 2:
                {
                    "user_id": "xxx@xxx",
                    "orgPersonType": "Staff",
                    "affiliation": "My Company"
                }

        """


class Saml2(ProtocolHandlerBase):

    name = "saml2"

    @classmethod
    def get_assertion_data(self, context, auth_payload):
        """Extract assertion data from the environment set by mod_shib
        or mod_mellon

        :param context: A dictionary with string keys and simple types as
                     values containing contextual data about the session.
        :param auth_payload: A dictionary containing client provided
        authentication data.
        :returns: A dictionary containing assertion data.
            Example assertion data:
                {
                    "user_id": "xxx@xxx",
                    "asserted_attribute_type1": "value1",
                    "asserted_attribute_type2": "value2"
                }
            Example 2:
                {
                    "user_id": "xxx@xxx",
                    "orgPersonType": "Staff",
                    "affiliation": "My Company"
                }

        """

        assertion = {}
        assertion["user_id"] = "xxx"
        assertion.update(self.get_assertion_params_from_env(context))
        return assertion

    @classmethod
    def get_assertion_params_from_env(self, context):
        prefix = CONF.federation.assertion_prefix
        for k, v in context['environment'].items():
            if k.startswith(prefix):
                yield (k, v)
