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

from saml2 import saml
from saml2 import samlp
import xmldsig
from xml.etree import cElementTree as ElementTree

from keystone.openstack.common import timeutils


def samlize_token(user_id, roles):

    """ Creating Subject
    <ns0:Subject>
        <ns0:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">8c520fea70434c6ea5bd04d2dc529d32</ns0:NameID>
        <ns0:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
            <ns0:SubjectConfirmationData Recipient="http://beta.com/Shibboleth.sso/SAML2/POST" />
        </ns0:SubjectConfirmation>
    </ns0:Subject>
    """
    name_id = saml.NameID()
    name_id.text = user_id
    name_id.format = saml.NAMEID_FORMAT_EMAILADDRESS
    subject_conf_data = saml.SubjectConfirmationData()
    subject_conf_data.recipient = "http://beta.com/Shibboleth.sso/SAML2/POST"
    subject_conf_data.not_on_or_after = timeutils.isotime()
    subject_conf = saml.SubjectConfirmation()
    subject_conf.method = saml.SCM_BEARER
    subject_conf.add_extension_element(subject_conf_data)
    subject = saml.Subject()
    subject.add_extension_element(subject_conf)
    subject.add_extension_element(name_id)

    """ Creating AttributeStatement
    <ns0:AttributeStatement xmlns:ns0="urn:oasis:names:tc:SAML:2.0:assertion" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <ns0:Attribute FriendlyName="keystone_user" Name="user" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
            <ns0:AttributeValue xsi:type="xs:string">e2d476e924df48b3b28a06d3b2c77501</ns0:AttributeValue>
        </ns0:Attribute>
        <ns0:Attribute FriendlyName="keystone_roles" Name="roles" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
            <ns0:AttributeValue xsi:type="xs:string">6328b7aecae6485c8e5c9c4ecec87689</ns0:AttributeValue>
        </ns0:Attribute>
    </ns0:AttributeStatement>
    """
    attribute_statement = saml.AttributeStatement()
    user_attribute = saml.Attribute()
    user_attribute.friendly_name = "keystone_user"
    user_attribute.name = "user"
    user_attribute.name_format = saml.NAME_FORMAT_URI
    user_value = saml.AttributeValue()
    user_value.text = user_id
    user_attribute.add_extension_element(user_value)

    roles_attribute = saml.Attribute()
    roles_attribute.friendly_name = "keystone_roles"
    roles_attribute.name = "roles"
    roles_attribute.name_format = saml.NAME_FORMAT_URI

    for role in roles:
        role_value = saml.AttributeValue()
        role_value.text = role
        roles_attribute.add_extension_element(role_value)

    attribute_statement.add_extension_element(user_attribute)
    attribute_statement.add_extension_element(roles_attribute)

    """ Creating AuthnStatement
    <ns0:AuthnStatement xmlns:ns0="urn:oasis:names:tc:SAML:2.0:assertion" AuthnInstant="2014-07-30T03:04:25Z" SessionIndex="47335964daae44799372ec4164ad1efb" SessionNotOnOrAfter="2014-07-30T03:04:26Z">
        <ns0:AuthnContext>
            <ns0:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</ns0:AuthnContextClassRef>
            <ns0:AuthenticatingAuthority>https://acme.com</ns0:AuthenticatingAuthority>
        </ns0:AuthnContext>
    </ns0:AuthnStatement>
    """
    authn_statement = saml.AuthnStatement()
    authn_statement.authn_instant = timeutils.isotime()
    authn_statement.session_index = uuid.uuid4().hex
    authn_statement.session_not_on_or_after = timeutils.isotime()
    authn_context = saml.AuthnContext()
    authn_context_class = saml.AuthnContextClassRef()
    authn_context_class.text = saml.AUTHN_PASSWORD
    authn_authority = saml.AuthenticatingAuthority()
    authn_authority.text = "https://acme.com"
    authn_context.add_extension_element(authn_context_class)
    authn_context.add_extension_element(authn_authority)
    authn_statement.add_extension_element(authn_context)

    """ Creating Issuer
    <ns0:Issuer xmlns:ns0="urn:oasis:names:tc:SAML:2.0:assertion" Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">https://acme.com/FIM/sps/openstack/saml20</ns0:Issuer>
    """
    issuer = saml.Issuer()
    issuer.format = saml.NAMEID_FORMAT_ENTITY
    issuer.text = "https://acme.com/FIM/sps/openstack/saml20"

    """ Creating Status
    <ns0:Status xmlns:ns0="urn:oasis:names:tc:SAML:2.0:protocol">
        <ns0:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success" />
    </ns0:Status>
    """
    status = samlp.Status()
    status_code = samlp.StatusCode()
    status_code.value = samlp.STATUS_SUCCESS
    status_code.text = ''
    status.add_extension_element(status_code)

    """ Creating Signature
    <ns0:Signature xmlns:ns0="http://www.w3.org/2000/09/xmldsig#" Id="2593c924545141f497717d43e12cbe71">
        <ns0:SignedInfo>
            <ns0:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
            <ns0:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
            <ns0:Reference URI="1492dddd21104b28bd80e793202a788a">
                <ns0:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
                <ns0:DigestValue>e1e43f0ac01140d9a0db7b78af29cf9e</ns0:DigestValue>
                <ns0:Transforms>
                    <ns0:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature" />
                </ns0:Transforms>
            </ns0:Reference>
        </ns0:SignedInfo>
        <ns0:SignatureValue>39c44b7668b942f98c9d9c06c534f9ad</ns0:SignatureValue>
    </ns0:Signature>
    """
    canonical_method = xmldsig.CanonicalizationMethod()
    canonical_method.algorithm = xmldsig.ALG_EXC_C14N
    sig_method = xmldsig.SignatureMethod()
    sig_method.algorithm = xmldsig.SIG_RSA_SHA1

    transforms = xmldsig.Transforms()
    transform = xmldsig.Transform()
    transform.algorithm = xmldsig.TRANSFORM_ENVELOPED
    transforms.add_extension_element(transform)

    digest_method = xmldsig.DigestMethod()
    digest_method.algorithm = xmldsig.DIGEST_SHA1
    digest_value = xmldsig.DigestValue()
    digest_value.text = uuid.uuid4().hex

    reference = xmldsig.Reference()
    reference.uri = uuid.uuid4().hex
    reference.add_extension_element(digest_method)
    reference.add_extension_element(digest_value)
    reference.add_extension_element(transforms)

    signed_info = xmldsig.SignedInfo()
    signed_info.add_extension_element(canonical_method)
    signed_info.add_extension_element(sig_method)
    signed_info.add_extension_element(reference)

    sig_value = xmldsig.SignatureValue()
    sig_value.text = uuid.uuid4().hex

    signature = xmldsig.Signature()
    signature.id = uuid.uuid4().hex
    signature.add_extension_element(signed_info)
    signature.add_extension_element(sig_value)

    """ Creating Assertion
    <saml:Assertion ID="Assertion-uuid8b9b70bf-0146-1b03-9aeb-8256bd3eea40" IssueInstant="2014-06-11T15:45:58Z" Version="2.0">
    Add Issuer, Signature, Subject, AuthnStatement and AttributeStatement
    """
    assertion = saml.Assertion()
    assertion.id = uuid.uuid4().hex
    assertion.issue_instant = timeutils.isotime()
    assertion.add_extension_element(issuer)
    assertion.add_extension_element(signature)
    assertion.add_extension_element(subject)
    assertion.add_extension_element(authn_statement)
    assertion.add_extension_element(attribute_statement)

    """ Creating Response
    <ns0:Response Destination="http://beta.com/Shibboleth.sso/SAML2/POST" ID="c5954543230e4e778bc5b92923a0512d" IssueInstant="2014-07-30T03:19:45Z" Version="2.0" />
    Add Issuer, Status and Assertion
    """
    response = samlp.Response()
    response.destination = "http://beta.com/Shibboleth.sso/SAML2/POST"
    response.id = uuid.uuid4().hex
    response.issue_instant = timeutils.isotime()
    response.version = "2.0"

    response.add_extension_element(issuer)
    response.add_extension_element(status)
    response.add_extension_element(assertion)

    envelope = ElementTree.fromstring(response.to_string())

    return envelope


SAMPLE_RESPONSE = """
    <samlp:Response xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Destination="http://beta.com/Shibboleth.sso/SAML2/POST" ID="FIMRSP_8b9b7213-0146-1b7b-a3d6-8256bd3eea40" IssueInstant="2014-06-11T15:45:58Z" Version="2.0">
      <saml:Issuer Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">https://acme.com/FIM/sps/openstack/saml20</saml:Issuer>
      <samlp:Status>
        <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success" />
      </samlp:Status>
      <saml:Assertion ID="Assertion-uuid8b9b70bf-0146-1b03-9aeb-8256bd3eea40" IssueInstant="2014-06-11T15:45:58Z" Version="2.0">
        <saml:Issuer Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">https://acme.com/FIM/sps/openstack/saml20</saml:Issuer>
        <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="uuid8b9b712a-0146-1d49-ab82-8256bd3eea40">
          <ds:SignedInfo>
          <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
          <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
          <ds:Reference URI="#Assertion-uuid8b9b70bf-0146-1b03-9aeb-8256bd3eea40">
            <ds:Transforms>
              <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature" />
              <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
              <xc14n:InclusiveNamespaces xmlns:xc14n="http://www.w3.org/2001/10/xml-exc-c14n#" PrefixList="xs saml xsi" />
              </ds:Transform>
            </ds:Transforms>
            <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
            <ds:DigestValue>VnHtyQ6Wgt6ACo4QaEsUBfNWJ4g=</ds:DigestValue>
          </ds:Reference>
          </ds:SignedInfo>
          <ds:SignatureValue>SmiSWB+iSks+8socnmSZzQ=</ds:SignatureValue>
          <ds:KeyInfo>
            <ds:X509Data>
              <ds:X509Certificate>MIICBzCCAXCgAwIBhikBMZPgdyQ==</ds:X509Certificate>
            </ds:X509Data>
          </ds:KeyInfo>
        </ds:Signature>
        <saml:Subject>
          <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">topol</saml:NameID>
          <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
            <saml:SubjectConfirmationData NotOnOrAfter="2014-06-11T15:46:58Z" Recipient="http://beta.com/Shibboleth.sso/SAML2/POST" />
          </saml:SubjectConfirmation>
        </saml:Subject>
        <saml:AuthnStatement AuthnInstant="2014-06-11T15:45:58Z" SessionIndex="uuid8b9b66e2-0146-1736-94c2-8256bd3eea40" SessionNotOnOrAfter="2014-06-11T16:45:56Z">
        <saml:AuthnContext>
          <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml:AuthnContextClassRef>
          <saml:AuthenticatingAuthority>https//acme.com</saml:AuthenticatingAuthority>
        </saml:AuthnContext>
        </saml:AuthnStatement>
        <saml:AttributeStatement>
          <saml:Attribute FriendlyName="keystone_user" Name="user" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
            <saml:AttributeValue xsi:type="xs:string">topol</saml:AttributeValue>
          </saml:Attribute>
          <saml:Attribute FriendlyName="keystone_roles" Name="roles" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
            <saml:AttributeValue xsi:type="xs:string">demo</saml:AttributeValue>
            <saml:AttributeValue xsi:type="xs:string">anotherrole</saml:AttributeValue>
          </saml:Attribute>
        </saml:AttributeStatement>
        </saml:Assertion>
      </samlp:Response>
    """
