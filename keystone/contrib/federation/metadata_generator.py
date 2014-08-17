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

from saml2 import md  # noqa
from saml2 import samlp  # noqa
import xmldsig as ds  # noqa

from keystone.common import config
from keystone.openstack.common import log


LOG = log.getLogger(__name__)
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

    def _create_entity_descriptor(self):
        ed = md.EntityDescriptor()
        ed.entity_id = CONF.federation.entity_id
        return ed

    def _create_idpssodescriptor(self):
        def get_cert():
            """Open and read certificate file.

            The function returns a certificate with the first and last lines
            stripped.

            :return: certificate
            :raises IOError: in case of opening reading certificate file.

            """
            try:
                with open(CONF.signing.certfile, 'r') as certificate:
                    return "".join(certificate.readlines()[1:-1])
            except IOError as e:
                msg = _("Canot open certificate %(cert_file)s. "
                        "Reason: %(reason)s")
                msg = msg % {'cert_file': CONF.signing.certfile, 'reason': e}
                LOG.error(msg)
                raise IOError(msg)

        def key_descriptor():
            cert = get_cert()
            return md.KeyDescriptor(
                key_info=ds.KeyInfo(
                    x509_data=ds.X509Data(
                        x509_certificate=ds.X509Certificate(text=cert)
                    )
                ), use='signing'
            )

        def single_sign_on_service():
            idp_sso_endpoint = CONF.federation.idp_sso_endpoint
            return md.SingleSignOnService(text=idp_sso_endpoint)

        idpsso = md.IDPSSODescriptor()
        idpsso.protocol_support_enumeration = samlp.NAMESPACE
        # NOTE(marek-denis): Add Extensions object
        idpsso.key_descriptor = key_descriptor()
        idpsso.single_sign_on_service = single_sign_on_service()
        return idpsso
