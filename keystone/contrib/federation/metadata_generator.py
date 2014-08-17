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
import subprocess
import tempfile
import uuid
import xml

import saml2
from saml2 import md
from saml2 import metadata
from saml2 import saml
from saml2 import samlp
import xmldsig

from keystone.common import config
from keystone.openstack.common import timeutils

CONF = config.CONF


class MetadataGenerator(object):
    """A class for generating SAML IdP Metadata."""

    def generate_metadata(self):
        """Generate Identity Provider Metadata.

        Generate and format into XML a metadata to be exposed and
        consumed by federated Service Providers.

        :return: <EntityDescriptor> object.

        """
        entity_descriptor = self._create_entity_descriptor()

        entity_descriptor.idpsso_descriptor = self._create_idpssodescriptor()

        return entity_descriptor

    def _get_cert():
        "Read certificate and strip 1st and last lines."""
        with open(CONF.idp_pubkey, 'r') as certificate:
            return "".join(certificate.readlines()[1:-1])

    def _create_entity_descriptor(self):
        return md.EntityDescriptor(entity_id = 'https://acme.com/idp')

    def _create_idpssodescriptor(self):
        idpsso = md.IDPSSODescriptor()
        idpsso.protocol_support_enumeration = samlp.NAMESPACE
        # NOTE(marek-denis): Add Extensions object
        idpsso.key_descriptor = self._create_keydescriptor()

        return idpsso

    def _create_keydescriptor(self):
        cert = self._get_cert()
        return md.KeyDescriptor(
                key_info=ds.KeyInfo(
                    x509_data=ds.X509Data(
                        x509_certificate=ds.X509Certificate(text=cert)
                    )
                ),
                use='signing'
            )

    def _create_singlesignonservice(self):
        return md.SingleSignOnService(text='acme.com/v3/OS-FEDERATION/SSO/')
