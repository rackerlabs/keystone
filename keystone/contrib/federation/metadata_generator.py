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

from saml2 import md
from saml2 import samlp
import xmldsig as ds

from keystone.common import config
from keystone.openstack.common import timeutils

CONF = config.CONF


class MetadataGenerator(object):
    """A class for generating SAML IdP Metadata."""

    ENTITY_ID_SUFFIX = '/v3/OS-FEDERATION/saml2'

    def __init__(self):
        self.sso_servive = 'https://acme.com/v3/OS-FEDERATION/SSO'

    def generate_metadata(self):
        """Generate Identity Provider Metadata.

        Generate and format into XML a metadata to be exposed and
        consumed by federated Service Providers.

        :return: <EntityDescriptor> object.

        """
        entity_descriptor = self._create_entity_descriptor()
        entity_descriptor.idpsso_descriptor = self._create_idpssodescriptor()
        return entity_descriptor

    def entity_id(self):
        """Create unique Identity Provider entity_id value.

        The value is either read diretly from the config file or created
        dynamically.

        :return: entity_id

        """
        if CONF.federation.entity_id:
            entity_id = CONF.federation.entity_id
        else:
            # FIXME(marek-denis): Add current Keystone hostname w/ domain.
            entity_id = 'https://acme.dynamite' + self.ENTITY_ID_SUFFIX
        return entity_id

    def _create_entity_descriptor(self):
        metadata_expiration_time = CONF.federation.metadata_expiration_time
        entity_id = CONF.federation.entity_id
        expires = datetime.timedelta(seconds=metadata_expiration_time)

        ed = md.EntityDescriptor()
        ed.entity_id = entity_id
        ed.valid_until = timeutils.utcnow() + expires
        return ed

    def _create_idpssodescriptor(self):
    """Create <IDPSSODesriptor> object."""

        def get_cert():
            """Open and read certificate file.

            The function strips first and last line.
            :return: certificate
            :raises IOError: in case of opening reading certificate file.

            """
            try:
                with open(CONF.idp_public_key, 'r') as certificate:
                    return "".join(certificate.readlines()[1:-1])
            except IOError as e:
                msg = ("Canot open certificate %(cert_file)s. "
                       "Reason: %(reason)s" % {
                           'cert_file': CONF.idp_public_key,
                           'reason': e
                       })
                raise IOError(msg)

        def keydescriptor():
            cert = get_cert()
            return md.KeyDescriptor(
                key_info=ds.KeyInfo(
                    x509_data=ds.X509Data(
                        x509_certificate=ds.X509Certificate(text=cert)
                    )
                ), use='signing'
            )

        idpsso = md.IDPSSODescriptor()
        idpsso.protocol_support_enumeration = samlp.NAMESPACE
        # NOTE(marek-denis): Add Extensions object
        idpsso.key_descriptor = keydescriptor()
        return idpsso

    def _create_singlesignonservice(self):
        return md.SingleSignOnService(text=self.sso_servive)

    # FIXME(marek-denis): Implement this method
    def _create_nameid(self):
        raise NotImplementedError()
