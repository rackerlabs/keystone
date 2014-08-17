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

import saml2  # noqa
from saml2 import md  # noqa
from saml2 import saml  # noqa
from saml2 import samlp  # noqa
import xmldsig  # noqa

from keystone.common import config
from keystone.i18n import _
from keystone.openstack.common import log
from keystone.openstack.common import timeutils


LOG = log.getLogger(__name__)
CONF = config.CONF


class SAMLGenerator(object):
    """A class to generate SAML assertions."""

    def __init__(self):
        self.assertion_id = uuid.uuid4().hex

    def samlize_token(self, issuer, recipient, user, roles, project,
                      expires_in=None):
        """Convert Keystone attributes to a SAML assertion.

        :param issuer: URL of the issuing party
        :type issuer: string
        :param recipient: URL of the recipient
        :type recipient: string
        :param user: Keystone user name
        :type user: string
        :param roles: Comma separated list of Keystone role names
        :type roles: list
        :param project: Keystone project name
        :type project: string
        :param expires_in: Sets how long the assertion is valid for, in seconds
        :type expires_in: int

        :return: XML <Response> object

        """
        expires_in = self._determine_expiration_time(expires_in)
        status = self._create_status()
        saml_issuer = self._create_issuer(issuer)
        subject = self._create_subject(user, expires_in, recipient)
        attribute_statement = self._create_attribute_statement(user, roles,
                                                               project)
        authn_statement = self._create_authn_statement(issuer, expires_in)
        signature = self._create_signature()

        assertion = self._create_assertion(saml_issuer, signature,
                                           subject, authn_statement,
                                           attribute_statement)

        assertion = self._sign_assertion(assertion)

        response = self._create_response(saml_issuer, status, assertion,
                                         recipient)
        return response

    def _determine_expiration_time(self, expires_in):
        if expires_in is None:
            expires_in = CONF.saml.assertion_expiration_time
        now = timeutils.utcnow()
        future = now + datetime.timedelta(seconds=expires_in)
        return timeutils.isotime(future, subsecond=True)

    def _create_status(self):
        """Creating Status
        <ns0:Status xmlns:ns0="urn:oasis:names:tc:SAML:2.0:protocol">
            <ns0:StatusCode
              Value="urn:oasis:names:tc:SAML:2.0:status:Success" />
        </ns0:Status>

        """
        status = samlp.Status()
        status_code = samlp.StatusCode()
        status_code.value = samlp.STATUS_SUCCESS
        status_code.set_text('')
        status.status_code = status_code
        return status

    def _create_issuer(self, issuer_name):
        """Creating Issuer
        <ns0:Issuer
          xmlns:ns0="urn:oasis:names:tc:SAML:2.0:assertion"
          Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">
          https://acme.com/FIM/sps/openstack/saml20</ns0:Issuer>

        """
        issuer = saml.Issuer()
        issuer.format = saml.NAMEID_FORMAT_ENTITY
        issuer.set_text(issuer_name)
        return issuer

    def _create_subject(self, user, expires_in, recipient):
        """Creating Subject
        <ns0:Subject>
            <ns0:NameID
              Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
                8c520fea70434c6ea5bd04d2dc529d32</ns0:NameID>
            <ns0:SubjectConfirmation
              Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                <ns0:SubjectConfirmationData
                  Recipient="http://beta.com/Shibboleth.sso/SAML2/POST" />
            </ns0:SubjectConfirmation>
        </ns0:Subject>

        :return: A <Subject> object

        """
        name_id = saml.NameID()
        name_id.set_text(user)
        name_id.format = saml.NAMEID_FORMAT_EMAILADDRESS
        subject_conf_data = saml.SubjectConfirmationData()
        subject_conf_data.recipient = recipient
        subject_conf_data.not_on_or_after = expires_in
        subject_conf = saml.SubjectConfirmation()
        subject_conf.method = saml.SCM_BEARER
        subject_conf.subject_confirmation_data = subject_conf_data
        subject = saml.Subject()
        subject.subject_confirmation = subject_conf
        subject.name_id = name_id
        return subject

    def _create_attribute_statement(self, user, roles, project):
        """Creating AttributeStatement
        <ns0:AttributeStatement
          xmlns:ns0="urn:oasis:names:tc:SAML:2.0:assertion"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:Attribute FriendlyName="keystone_user" Name="user"
              NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
                <ns0:AttributeValue
                  xsi:type="xs:string">test_user</ns0:AttributeValue>
            </ns0:Attribute>
            <ns0:Attribute FriendlyName="keystone_roles" Name="roles"
              NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
                <ns0:AttributeValue
                  xsi:type="xs:string">admin</ns0:AttributeValue>
                <ns0:AttributeValue
                  xsi:type="xs:string">member</ns0:AttributeValue>
            </ns0:Attribute>
            <ns0:Attribute FriendlyName="keystone_projects" Name="projects"
              NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
                <ns0:AttributeValue
                  xsi:type="xs:string">development</ns0:AttributeValue>
            </ns0:Attribute>
        </ns0:AttributeStatement>

        :return: A <AttributeStatement> object

        """
        user_attribute = saml.Attribute()
        user_attribute.friendly_name = "keystone_user"
        user_attribute.name = "user"
        user_attribute.name_format = saml.NAME_FORMAT_URI
        user_value = saml.AttributeValue()
        user_value.set_text(user)
        user_attribute.attribute_value = user_value

        roles_attribute = saml.Attribute()
        roles_attribute.friendly_name = "keystone_roles"
        roles_attribute.name = "roles"
        roles_attribute.name_format = saml.NAME_FORMAT_URI

        for role in roles:
            role_value = saml.AttributeValue()
            role_value.set_text(role)
            roles_attribute.attribute_value.append(role_value)

        project_attribute = saml.Attribute()
        project_attribute.friendly_name = "keystone_project"
        project_attribute.name = "project"
        project_attribute.name_format = saml.NAME_FORMAT_URI
        project_value = saml.AttributeValue()
        project_value.set_text(project)
        project_attribute.attribute_value = project_value

        attribute_statement = saml.AttributeStatement()
        attribute_statement.attribute.append(user_attribute)
        attribute_statement.attribute.append(roles_attribute)
        attribute_statement.attribute.append(project_attribute)
        return attribute_statement

    def _create_authn_statement(self, issuer, expires_in):
        """Creating AuthnStatement
        <ns0:AuthnStatement xmlns:ns0="urn:oasis:names:tc:SAML:2.0:assertion"
          AuthnInstant="2014-07-30T03:04:25Z" SessionIndex="47335964efb"
          SessionNotOnOrAfter="2014-07-30T03:04:26Z">
            <ns0:AuthnContext>
                <ns0:AuthnContextClassRef>
                  urn:oasis:names:tc:SAML:2.0:ac:classes:Password
                </ns0:AuthnContextClassRef>
                <ns0:AuthenticatingAuthority>
                  https://acme.com/FIM/sps/openstack/saml20
                </ns0:AuthenticatingAuthority>
            </ns0:AuthnContext>
        </ns0:AuthnStatement>

        :return: A <AuthnStatement> object

        """
        authn_statement = saml.AuthnStatement()
        authn_statement.authn_instant = timeutils.isotime()
        authn_statement.session_index = uuid.uuid4().hex
        authn_statement.session_not_on_or_after = expires_in

        authn_context = saml.AuthnContext()
        authn_context_class = saml.AuthnContextClassRef()
        authn_context_class.set_text(saml.AUTHN_PASSWORD)

        authn_authority = saml.AuthenticatingAuthority()
        authn_authority.set_text(issuer)
        authn_context.authn_context_class_ref = authn_context_class
        authn_context.authenticating_authority = authn_authority

        authn_statement.authn_context = authn_context

        return authn_statement

    def _create_assertion(self, issuer, signature, subject, authn_statement,
                          attribute_statement):
        """Creating Assertion
        <saml:Assertion
          ID="Assertion-uuid8b9b70bf-0146-1b03-9aeb-8256bd3eea40"
          IssueInstant="2014-06-11T15:45:58Z"
          Version="2.0">

        """
        assertion = saml.Assertion()
        assertion.id = self.assertion_id
        assertion.issue_instant = timeutils.isotime()
        assertion.issuer = issuer
        assertion.signature = signature
        assertion.subject = subject
        assertion.authn_statement = authn_statement
        assertion.attribute_statement = attribute_statement
        return assertion

    def _create_response(self, issuer, status, assertion, recipient):
        """Creating Response
        <ns0:Response
          Destination="http://beta.com/Shibboleth.sso/SAML2/POST"
          ID="c5954543230e4e778bc5b92923a0512d"
          IssueInstant="2014-07-30T03:19:45Z"
          Version="2.0" />

        """
        response = samlp.Response()
        response.id = uuid.uuid4().hex
        response.destination = recipient
        response.issue_instant = timeutils.isotime()
        response.version = "2.0"
        response.issuer = issuer
        response.status = status
        response.assertion = assertion
        return response

    def _create_signature(self):
        """Add a <Signature> template


        This must be filled with algorithms that the signing binary will apply
        in order to sign the whole message.
        Currently we enforce X509 signing.
        Example of the template::

        <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
          <SignedInfo>
            <CanonicalizationMethod
              Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
            <SignatureMethod
              Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
            <Reference URI="#<Assertion ID>">
              <Transforms>
                <Transform
            Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
               <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
              </Transforms>
             <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
             <DigestValue />
            </Reference>
          </SignedInfo>
          <SignatureValue />
          <KeyInfo>
            <X509Data />
          </KeyInfo>
        </Signature>

        :return: XML <Signature> object

        """
        canonical_method = xmldsig.CanonicalizationMethod()
        canonical_method.algorithm = xmldsig.ALG_EXC_C14N
        signature_method = xmldsig.SignatureMethod(
            algorithm=xmldsig.SIG_RSA_SHA1)

        transforms = xmldsig.Transforms()
        envelope_transform = xmldsig.Transform(
            algorithm=xmldsig.TRANSFORM_ENVELOPED)

        c14_transform = xmldsig.Transform(algorithm=xmldsig.ALG_EXC_C14N)
        transforms.transform = [envelope_transform, c14_transform]

        # digest method
        digest_method = xmldsig.DigestMethod(algorithm=xmldsig.DIGEST_SHA1)
        # digest value
        digest_value = xmldsig.DigestValue()

        reference = xmldsig.Reference()
        reference.uri = '#' + self.assertion_id
        reference.digest_method = digest_method
        reference.digest_value = digest_value
        reference.transforms = transforms

        signed_info = xmldsig.SignedInfo()
        signed_info.canonicalization_method = canonical_method
        signed_info.signature_method = signature_method
        signed_info.reference = reference

        x509_data = xmldsig.X509Data()

        key_info = xmldsig.KeyInfo()
        key_info.x509_data = x509_data

        signature_value = xmldsig.SignatureValue()

        signature = xmldsig.Signature()
        signature.signed_info = signed_info
        signature.signature_value = signature_value
        signature.key_info = key_info

        return signature

    def _sign_assertion(self, assertion):
        """Sign SAML assertion

        This method utilizes ``xmlsec1`` binary and signs SAML assertions in a
        separate process. ``xmlsec1`` cannot read input data from stdin so the
        prepared assertion needs to be serialized and stored in a temporary
        file. ``tempfile.NamedTemporaryFile()`` was used here as it deletes the
        file from the file-system after the Python file object is closed.
        The signed assertion is redirected to standard output and read using
        subprocess.PIPE redirection. A ``saml.Assertion`` class is created
        again from the signed string and returned.

        Parameters that are required in the CONF::
        * xmlsec_binary
        * private key file path
        * public key file path
        * assertions_dir - directory where temporary files will be stored.
                           This value should default to '/tmp'
        :return: A signed <Assertion> object

        """
        def estimate_id_tag(assertion):
            attributes = assertion.c_attributes.keys()
            if 'ID' in attributes:
                return ('--id-attr:ID', 'Assertion')
            if 'id' in attributes:
                return ('--id-attr:id', 'Assertion')
            else:
                return None

        xmlsec_binary = CONF.federation.xmlsec1_binary
        idp_private_key = CONF.signing.keyfile
        idp_public_key = CONF.signing.certfile
        assertions_dir = CONF.federationl.assertions_dir

        # xmlsec1 --sign --privkey-pem privkey.pem,cert.pem tosign.xml
        certificates = "%(idp_private_key)s,%(idp_public_key)s" % {
            'idp_public_key': idp_public_key,
            'idp_private_key': idp_private_key
        }

        try:
            assertion_file = tempfile.NamedTemporaryFile(dir=assertions_dir)
            assertion_file.write(assertion.to_string())
            assertion_file.flush()
        except IOError as e:
            msg = _("Cannot create temporary SAML assertion at: %(name)s. "
                    "Reason: %(reason)s")
            msg = msg % {"name": assertion_file.name, "reason": e}
            LOG.error(msg)
            raise IOError(msg)

        command_list = [xmlsec_binary, '--sign', '--privkey-pem', certificates]
        id_tags = estimate_id_tag(assertion)
        if id_tags:
            command_list.extend(id_tags)
        command_list.append(assertion_file.name)
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        output_stdout = process.stdout.read()
        try:
            signed_assertion = saml2.create_class_from_xml_string(
                saml.Assertion, output_stdout)
        except xml.etree.ElementTree.ParseError:
            raise
        else:
            return signed_assertion


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
        ed.entity_id = CONF.saml.idp_entity_id
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
                key_info=xmldsig.KeyInfo(
                    x509_data=xmldsig.X509Data(
                        x509_certificate=xmldsig.X509Certificate(text=cert)
                    )
                ), use='signing'
            )

        def single_sign_on_service():
            idp_sso_endpoint = CONF.saml.idp_sso_endpoint
            return md.SingleSignOnService(text=idp_sso_endpoint)

        def organization():
            name = CONF.saml.idp_organization_name
            display_name = CONF.saml.idp_organization_display_name
            url = CONF.saml.idp_organization_url
            return md.Organization(
                organization_display_name=display_name,
                organization_url=url, organization_name=name)

        def contact_person():
            company = CONF.saml.idp_contact_company
            given_name = CONF.saml.idp_contact_name
            surname = CONF.saml.idp_contact_surname
            email = CONF.saml.idp_contact_email
            telephone = CONF.saml.idp_contact_telephone

            return md.ContactPerson(
                company=company, given_name=given_name, sur_name=surname,
                email_address=email, telephone_number=telephone)

        idpsso = md.IDPSSODescriptor()
        idpsso.protocol_support_enumeration = samlp.NAMESPACE
        idpsso.key_descriptor = key_descriptor()
        idpsso.single_sign_on_service = single_sign_on_service()
        idpsso.organization = organization()
        idpsso.contact_person = contact_person()
        return idpsso
