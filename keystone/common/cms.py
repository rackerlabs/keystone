# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import hashlib
import string

from keystone.common import environment
from keystone.openstack.common import log as logging


LOG = logging.getLogger(__name__)
HEX_TOKEN_LEN = 32


def cms_verify(formatted, signing_cert_file_name, ca_file_name):
    """Verifies the signature of the contents IAW CMS syntax."""
    process = environment.subprocess.Popen(["openssl", "cms", "-verify",
                                            "-certfile",
                                            signing_cert_file_name,
                                            "-CAfile", ca_file_name,
                                            "-inform", "PEM",
                                            "-nosmimecap", "-nodetach",
                                            "-nocerts", "-noattr"],
                                           stdin=environment.subprocess.PIPE,
                                           stdout=environment.subprocess.PIPE,
                                           stderr=environment.subprocess.PIPE)
    output, err = process.communicate(formatted)
    retcode = process.poll()
    if retcode:
        LOG.error(_('Verify error: %s') % err)
        raise environment.subprocess.CalledProcessError(retcode,
                                                        "openssl", output=err)
    return output


def token_to_cms(signed_text):
    copy_of_text = signed_text.replace('-', '/')

    formatted = "-----BEGIN CMS-----\n"
    line_length = 64
    while len(copy_of_text) > 0:
        if (len(copy_of_text) > line_length):
            formatted += copy_of_text[:line_length]
            copy_of_text = copy_of_text[line_length:]
        else:
            formatted += copy_of_text
            copy_of_text = ""
        formatted += "\n"

    formatted += "-----END CMS-----\n"

    return formatted


def verify_token(token, signing_cert_file_name, ca_file_name):
    return cms_verify(token_to_cms(token),
                      signing_cert_file_name,
                      ca_file_name)


def is_hex_token(token):
    """
    Determine if a token appears to a hex UUID or a hex-hashed
    PKI token.  In both cases we expect a token length of 32 and
    the contents to be hex.
    """
    if set(token) - set(string.hexdigits) and len(token) == HEX_TOKEN_LEN:
        return True


def cms_sign_text(text, signing_cert_file_name, signing_key_file_name):
    """Uses OpenSSL to sign a document
    Produces a Base64 encoding of a DER formatted CMS Document
    http://en.wikipedia.org/wiki/Cryptographic_Message_Syntax
    """
    process = environment.subprocess.Popen(["openssl", "cms", "-sign",
                                            "-signer", signing_cert_file_name,
                                            "-inkey", signing_key_file_name,
                                            "-outform", "PEM",
                                            "-nosmimecap", "-nodetach",
                                            "-nocerts", "-noattr"],
                                           stdin=environment.subprocess.PIPE,
                                           stdout=environment.subprocess.PIPE,
                                           stderr=environment.subprocess.PIPE)
    output, err = process.communicate(text)
    retcode = process.poll()
    if retcode or "Error" in err:
        if retcode == 3:
            LOG.error(_("Signing error: Unable to load certificate - "
                      "ensure you've configured PKI with "
                      "'keystone-manage pki_setup'"))
        else:
            LOG.error(_('Signing error: %s') % err)
        raise environment.subprocess.CalledProcessError(retcode, "openssl")
    return output


def cms_sign_token(text, signing_cert_file_name, signing_key_file_name):
    output = cms_sign_text(text, signing_cert_file_name, signing_key_file_name)
    return cms_to_token(output)


def cms_to_token(cms_text):

    start_delim = "-----BEGIN CMS-----"
    end_delim = "-----END CMS-----"
    signed_text = cms_text
    signed_text = signed_text.replace('/', '-')
    signed_text = signed_text.replace(start_delim, '')
    signed_text = signed_text.replace(end_delim, '')
    signed_text = signed_text.replace('\n', '')

    return signed_text


def cms_hash_token(token_id):
    """Hash PKI tokens.

    return: for ans1_token, returns the hash of the passed in token
            otherwise, returns what it was passed in.
    """
    if token_id is None:
        return None
    if not is_hex_token(token_id):
        hasher = hashlib.md5()
        hasher.update(token_id)
        return hasher.hexdigest()
    else:
        return token_id
