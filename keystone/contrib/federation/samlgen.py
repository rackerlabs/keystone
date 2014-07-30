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

from saml2 import saml
from saml2 import samlp
import xmldsig

from keystone.openstack.common import timeutils


class SAMLGenerator(object):
    """A class to generate SAML assertions."""

    def samlize_token(self, issuer, subject, roles, public_key, private_key,
                      expires_in):
        """Convert Keystone attributes to a SAML assertion.

        :param issuer: URL of an Identity Provider
        :type issuer: string
        :param subject: SAML subject, likely a user_id
        :type subject: string
        :param roles: Comma separated list of role names
        :type roles: list
        :param public_key: Location of public key to decrypt assertion
        :type public_key: string
        :param private_key: Location of private key use to sign assertion
        :type private_key: string
        :param expires_in: Sets how long the assertion is valid for, in days
        :type expires_in: int
        """

        now = timeutils.utcnow()
        future = now + datetime.timedelta(days=expires_in)
        expires_in = timeutils.isotime(future, subsecond=True)

        status = self._create_status()
        saml_issuer = self._create_issuer(issuer)
        saml_subject = self._create_subject(subject, issuer, expires_in)
        attribute_statement = self._create_attribute_statement(subject, roles)
        authn_statement = self._create_authn_statement(issuer, expires_in)
        signature = self._create_signature(public_key, private_key)

        assertion = self._create_assertion(saml_issuer, signature,
                                           saml_subject, authn_statement,
                                           attribute_statement)
        response = self._create_response(saml_issuer, status, assertion)
        return response

    def _create_subject(self, subject, issuer, expires_in):
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
        """
        name_id = saml.NameID()
        name_id.set_text(subject)
        name_id.format = saml.NAMEID_FORMAT_EMAILADDRESS
        subject_conf_data = saml.SubjectConfirmationData()
        subject_conf_data.recipient = issuer
        subject_conf_data.not_on_or_after = expires_in
        subject_conf = saml.SubjectConfirmation()
        subject_conf.method = saml.SCM_BEARER
        subject_conf.subject_confirmation_data = subject_conf_data
        subject = saml.Subject()
        subject.subject_confirmation = subject_conf
        subject.name_id = name_id
        return subject

    def _create_attribute_statement(self, subject, roles):
        """Creating AttributeStatement
        <ns0:AttributeStatement
          xmlns:ns0="urn:oasis:names:tc:SAML:2.0:assertion"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:Attribute FriendlyName="keystone_user" Name="user"
              NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
                <ns0:AttributeValue
                  xsi:type="xs:string">e2d7501</ns0:AttributeValue>
            </ns0:Attribute>
            <ns0:Attribute FriendlyName="keystone_roles" Name="roles"
              NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
                <ns0:AttributeValue
                  xsi:type="xs:string">6328b7a</ns0:AttributeValue>
            </ns0:Attribute>
        </ns0:AttributeStatement>
        """
        attribute_statement = saml.AttributeStatement()
        user_attribute = saml.Attribute()
        user_attribute.friendly_name = "keystone_user"
        user_attribute.name = "user"
        user_attribute.name_format = saml.NAME_FORMAT_URI
        user_value = saml.AttributeValue()
        user_value.set_text(subject)
        user_attribute.attribute_value = user_value

        roles_attribute = saml.Attribute()
        roles_attribute.friendly_name = "keystone_roles"
        roles_attribute.name = "roles"
        roles_attribute.name_format = saml.NAME_FORMAT_URI

        for role in roles:
            role_value = saml.AttributeValue()
            role_value.set_text(role)
            roles_attribute.attribute_value.append(role_value)

        attribute_statement.attribute.append(user_attribute)
        attribute_statement.attribute.append(roles_attribute)
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
                  https://acme.com
                </ns0:AuthenticatingAuthority>
            </ns0:AuthnContext>
        </ns0:AuthnStatement>
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

    def _create_assertion(self, issuer, signature, subject, authn_statement,
                          attribute_statement):
        """Creating Assertion
        <saml:Assertion
          ID="Assertion-uuid8b9b70bf-0146-1b03-9aeb-8256bd3eea40"
          IssueInstant="2014-06-11T15:45:58Z"
          Version="2.0">
        """
        assertion = saml.Assertion()
        assertion.id = uuid.uuid4().hex
        assertion.issue_instant = timeutils.isotime()
        assertion.issuer = issuer
        assertion.signature = signature
        assertion.subject = subject
        assertion.authn_statement = authn_statement
        assertion.attribute_statement = attribute_statement
        return assertion

    def _create_response(self, issuer, status, assertion):
        """Creating Response
        <ns0:Response
          Destination="http://beta.com/Shibboleth.sso/SAML2/POST"
          ID="c5954543230e4e778bc5b92923a0512d"
          IssueInstant="2014-07-30T03:19:45Z"
          Version="2.0" />
        """
        response = samlp.Response()
        # NOTE(stevemar): Not sure if destination needs to be set...
        # response.destination = "http://beta.com/Shibboleth.sso/SAML2/POST"
        response.id = uuid.uuid4().hex
        response.issue_instant = timeutils.isotime()
        response.version = "2.0"
        response.issuer = issuer
        response.status = status
        response.assertion = assertion
        return response

    def _create_signature(self, public_key, private_key):
        """Creating Signature

        :param public_key: location of public key (i.e., saml.crt)
        :type public_key: string
        :param private_key: location of private key (i.e., saml.pkcs8)
        :type private_key: string

        <ns0:Signature xmlns:ns0="http://www.w3.org/2000/09/xmldsig#"
            Id="2593c924545141f497717d43e12cbe71">
            <ns0:SignedInfo>
                <ns0:CanonicalizationMethod
                  Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
                <ns0:SignatureMethod
                  Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
                <ns0:Reference URI="1492dddd21104b28bd80e793202a788a">
                    <ns0:DigestMethod
                      Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
                    <ns0:DigestValue>e1e43f0ac01140d9a0</ns0:DigestValue>
                    <ns0:Transforms>
                        <ns0:Transform
                          Algorithm="xmldsig#enveloped-signature"/>
                    </ns0:Transforms>
                </ns0:Reference>
            </ns0:SignedInfo>
            <ns0:SignatureValue>39c44b7668b942f98c9d9c065</ns0:SignatureValue>
        </ns0:Signature>
        """
        key_data = open(public_key).read()
        digest_text = uuid.uuid4().hex

        canonical_method = xmldsig.CanonicalizationMethod()
        canonical_method.algorithm = xmldsig.ALG_EXC_C14N
        sig_method = xmldsig.SignatureMethod()
        sig_method.algorithm = xmldsig.SIG_RSA_SHA1

        transforms = xmldsig.Transforms()
        transform = xmldsig.Transform()
        transform.algorithm = xmldsig.TRANSFORM_ENVELOPED
        transforms.transform = transform

        digest_method = xmldsig.DigestMethod()
        digest_method.algorithm = xmldsig.DIGEST_SHA1
        digest_value = xmldsig.DigestValue()
        digest_value.set_text(digest_text)

        reference = xmldsig.Reference()
        reference.uri = uuid.uuid4().hex
        reference.digest_method = digest_method
        reference.digest_value = digest_value
        reference.transforms = transforms

        signed_info = xmldsig.SignedInfo()
        signed_info.canonicalization_method = canonical_method
        signed_info.signature_method = sig_method
        signed_info.reference = reference

        sig_value = xmldsig.SignatureValue()
        sig_value.set_text(key_data)

        signature = xmldsig.Signature()
        signature.id = uuid.uuid4().hex
        signature.signed_info = signed_info
        signature.signature_value = sig_value
        return signature
