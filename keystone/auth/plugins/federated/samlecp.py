# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

'''
Created on 14 Jan 2014

@author: kwss

Formulates AuthnRequests and validates SAML assertions returning
the result to the core federated module for trust management
using the ECP profile

'''
import base64
import libxml2
import time
import uuid
import xmlsec
import zlib

from keystone.auth.plugins import federated
from keystone.common import config
from keystone import exception
from keystone.openstack.common import log as logging

CONF = config.CONF

LOG = logging.getLogger(__name__)

METHOD_NAME = 'saml'
SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
SAMLP_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"

# Init libxml library
libxml2.initParser()
libxml2.substituteEntitiesDefault(1)

    # Init xmlsec library
if xmlsec.init() < 0:
    LOG.debug("Error: xmlsec initialization failed.")

    # Check loaded library version
if xmlsec.checkVersion() != 1:
    LOG.debug("Error: loaded xmlsec library version is not compatible.")

    # Init crypto library
if xmlsec.cryptoAppInit(None) < 0:
    LOG.debug("Error: crypto initialization failed.")

    # Init xmlsec-crypto library
if xmlsec.cryptoInit() < 0:
    LOG.debug("Error: xmlsec-crypto initialization failed.")


class SAML(federated.FederatedHandler):
    '''Validate the SAMLResponse contained in the auth_payload
       auth_payload = {
           "protocol_data": <SAMLResponse>,
           "provider_id": <provider_id>,
           "validation": {
               "certdata": <certificate-location>,
               "identifier_attribute": <user_id_attribute>
           }
        }
    '''
    def validate(self, auth_payload):
        if not auth_payload.get("provider_id"):
            raise exception.NotFound("Missing Provider ID")
        resp = {"response": None}
        self.discovery_service.populate_auth_dict(auth_payload,
                                                  auth_payload.get(
                                                      "provider_id"))

        # Get the validation information
        validation = auth_payload.get("validation")
        if not validation:
            raise exception.ValidationError(attribute="validation",
                                            target=auth_payload)
        unique_attribute = validation.get("identifier_attribute", None)
        assertion = auth_payload.get("protocol_data")
        if not assertion:
            raise exception.ValidationError(attribute="protocol_data",
                                            target=auth_payload)
        assertion = libxml2.parseDoc(self.parse_response(assertion,
                                                         validation))
        atts = {}
        names = []
        ctxt = assertion.xpathNewContext()
        ctxt.xpathRegisterNs("saml", SAML_NS)
        conditions = ctxt.xpathEval('//saml:Conditions')
        for cond in conditions:
            expires = cond.prop("NotOnOrAfter")

        for name in ctxt.xpathEval('//saml:NameID'):
            names.append(name.content)

        attributes = ctxt.xpathEval('//saml:Attribute')
        for att in attributes:
            ats = []
            ctxt.setContextNode(att)
            for value in ctxt.xpathEval('child::saml:AttributeValue'):
                ats.append(value.content)
            atts[att.prop("Name")] = ats
        if unique_attribute is not None:
            if atts.get(unique_attribute, None) is not None:
                names = atts.get(unique_attribute)
        attribute_set = {}
        attribute_set["attributes"] = atts
        attribute_set["provider"] = auth_payload["provider_id"]
        resp['uid'] = names[0]
        resp['user_identity'] = [attribute_set]
        resp['validity_time'] = expires
        return resp

    def sign(self, doc, request, key_file):
        xmlsec.addIDs(doc, request, ["ID"])
        node = xmlsec.findNode(request,
                               xmlsec.NodeSignature,
                               xmlsec.DSigNs)
        dsigCtx = xmlsec.DSigCtx()
        if node:
            key = xmlsec.cryptoAppKeyLoad(key_file,
                                          xmlsec.KeyDataFormatPem,
                                          None,
                                          None,
                                          None)
            dsigCtx.signKey = key
            dsigCtx.sign(node)
        req = doc.serialize()
        self.cleanup(doc, dsigCtx)
        return req

    def request(self, auth_payload):
        if not auth_payload.get("provider_id", None):
            raise exception.NotFound("Missing Provider ID")
        self.discovery_service.populate_auth_dict(auth_payload,
                                                  auth_payload.get(
                                                      "provider_id"))
        endpoint = auth_payload.get("endpoint")
        if not endpoint:
            raise exception.ValidationError(attribute="endpoint",
                                            target=auth_payload)
        provider = auth_payload.get("provider_id")
        if not provider:
            raise exception.ValidationError(attribute="provider",
                                            target=auth_payload)
        self.tmpl_req = """
            <S:Envelope xmlns:S="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:ecp="urn:oasis:names:tc:SAML:2.0:profiles:SSO:ecp">
            <S:Header/><S:Body><samlp:AuthnRequest
            xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
            xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
            ID="" URI=""
            Version="2.0"
            IssueInstant=""
            AssertionConsumerServiceIndex="1"
            AttributeConsumingServiceIndex="1"
            ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:PAOS">
            <saml:Issuer></saml:Issuer>
            <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
            <SignedInfo>
            <CanonicalizationMethod
            Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
            <SignatureMethod
            Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
            <Reference URI="">
            <Transforms>
            <Transform
            Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
            </Transforms>
            <DigestMethod
            Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
            <DigestValue/>
            </Reference>
            </SignedInfo>
            <SignatureValue/>
            </Signature>
            <samlp:NameIDPolicy
            AllowCreate="true"
            Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient"/>
            </samlp:AuthnRequest></S:Body></S:Envelope>"""
        return {"response": {"endpoint": endpoint,
                "protocol_data": self._create_request(
                    self.tmpl_req,
                    provider,
                    CONF.federated.get("request_signing_key")),
                "provider_id": provider}}

    def _create_request(self, request, provider, key):
        issue_instant = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        new_id = uuid.uuid4().hex
        doc = libxml2.parseDoc(request)
        ctxt = doc.xpathNewContext()
        ctxt.xpathRegisterNs("saml", SAML_NS)
        ctxt.xpathRegisterNs("samlp", SAMLP_NS)
        ctxt.xpathRegisterNs("ds", DS_NS)
        result = ctxt.xpathEval('//samlp:AuthnRequest')
        result[0].setProp("ID", new_id)
        result[0].setProp("URI", new_id)
        result[0].setProp("IssueInstant", issue_instant)
        result2 = ctxt.xpathEval('//saml:Issuer')
        for node in result2:
            node.setContent(CONF.federated.SPName)
            result2 = ctxt.xpathEval('//ds:Reference')
            result2[0].setProp("URI", "#" + new_id)
            ctxt.xpathFreeContext()
        return self.encodeReq(self.sign(doc, result[0], key))

    def deflate(self, data, compresslevel=9):
        compress = zlib.compressobj(
            compresslevel,
            zlib.DEFLATED,
            -zlib.MAX_WBITS,
            zlib.DEF_MEM_LEVEL,
            0)
        deflated = compress.compress(data)
        deflated += compress.flush()
        return deflated

    def inflate(self, data):
        decompress = zlib.decompressobj(
            -zlib.MAX_WBITS
        )
        inflated = decompress.decompress(data)
        inflated += decompress.flush()
        return inflated

    def encodeReq(self, req):
        req = base64.b64encode(req)
        return req

    def verify_file(self, xml_file, key_file):
        doc = libxml2.parseDoc(xml_file)
        xmlsec.addIDs(doc, doc.getRootElement(), ["ID"])
        if doc is None or doc.getRootElement() is None:
            return self.cleanup(doc)
        # Find start node
        node = xmlsec.findNode(doc.getRootElement(),
                               xmlsec.NodeSignature,
                               xmlsec.DSigNs)
         # Create signature context
        dsig_ctx = xmlsec.DSigCtx()
        key = xmlsec.cryptoAppKeyLoad(str(key_file),
                                      xmlsec.KeyDataFormatCertPem,
                                      None,
                                      None,
                                      None)
        dsig_ctx.signKey = key
        if key.setName(str(key_file)) < 0:
            return self.cleanup(doc, dsig_ctx)
        if dsig_ctx is None:
            return self.cleanup(doc)
        # Verify signature
        if dsig_ctx.verify(node) < 0:
            return self.cleanup(doc, dsig_ctx)
        if dsig_ctx.status == xmlsec.DSigStatusSucceeded:
            res = True
        else:
            res = False
        self.cleanup(doc, dsig_ctx, 1)
        return res

    def cleanup(self, doc=None, dsig_ctx=None, res=-1):
        if dsig_ctx is not None:
            dsig_ctx.destroy()
        if doc is not None:
            doc.freeDoc()
        return res

    def parse_response(self, assertion, validation):
        if self.verify_file(assertion, validation.get("certdata")):
            return assertion
        else:
            raise exception.Unauthorized()
