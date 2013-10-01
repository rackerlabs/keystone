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

import base64
import hashlib

from keystone.common import base64utils
from keystone.common import environment
from keystone.common import pemutils
from keystone.openstack.common import log as logging


LOG = logging.getLogger(__name__)
PKI_ANS1_PREFIX = 'MII'


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


def cms_pem_to_token_id(cms_pem):
    '''Convert cms pem to a token_id which is URL safe

    The cms data will be encoded in base64 to be used as a token id.

    token id's are utilized in various HTTP contexts:
        * URL components
        * HTTP header values

    Therefore it is essential the token id be safe to use in these
    contexts. Standard base64 is NOT safe.

    base64url text is designed to be safe for use in filenames and
    URL's. It is defined in RFC-4648 Section 5.

    base64url differs from base64 in the last two alphabet characters
    at index 62 and 63, these are sometimes referred as the
    altchars. The '+' character at index 62 is replaced by '-'
    (hyphen) and the '/' character at index 63 is replaced by '_'
    (underscore).

    base64url continues to use the '=' pad character which is NOT URL
    safe. RFC-4648 suggests two alternate methods to deal with this.

    percent-encode
        percent-encode the pad character (e.g. '=' becomes
        '%3D'). This makes the base64url text fully safe. But
        percent-enconding has the downside of requiring
        percent-decoding prior to feeding the base64url text into a
        base64url decoder since most base64url decoders do not
        recognize %3D as a pad character and most decoders require
        correct padding.

    no-padding
        padding is not strictly necessary to decode base64 or
        base64url text, the pad can be computed from the input text
        length. However many decoders demand padding and will consider
        non-padded text to be malformed. If one wants to omit the
        trailing pad character(s) for use in URL's it can be added back
        using the base64utils.base64_assure_padding() function.

    For our use we elect to strip the padding rather than
    percent-encode the padding. This makes the token id slightly
    shorter and cleaner.

    :param cms_pem: text containing cms data in PEM format
    :returns: a URL safe token_id
    '''

    # Extract the bindary data from the PEM formatted input
    binary_data = pemutils.get_pem_data(cms_pem, 'cms')
    if binary_data is None:
        raise ValueError('no pem found in cms_pem')

    # Encode binary data with a URL safe base64 alphabet
    text = base64.urlsafe_b64encode(binary_data)

    # Strip the padding because it's not URL safe
    token_id = base64utils.base64_strip_padding(text)

    return token_id


def token_id_to_cms_pem(token_id):
    '''Convert a URL safe token_id to cms data in PEM format

    See cms_pem_to_token_id() for a full explanation of how the token
    id encodes the cms data.

    :param token_id: a URL safe string containing CMS data
    :returns: cms data in PEM format
    '''

    # Restore padding because urlsafe_b64decode demands correct padding
    text = base64utils.base64_assure_padding(token_id)

    # Decode the URL safe base64 back into binary data
    binary_data = base64.urlsafe_b64decode(text)

    # Format the binary data into PEM format
    cms_pem = pemutils.binary_to_pem(binary_data, 'cms')
    return cms_pem


def verify_token(token, signing_cert_file_name, ca_file_name):
    return cms_verify(token_id_to_cms_pem(token),
                      signing_cert_file_name,
                      ca_file_name)


def is_ans1_token(token):
    """Determine if a token appears to be PKI-based.

    thx to ayoung for sorting this out.

    base64 decoded hex representation of MII is 3082
    In [3]: binascii.hexlify(base64.b64decode('MII='))
    Out[3]: '3082'

    re: http://www.itu.int/ITU-T/studygroups/com17/languages/X.690-0207.pdf

    pg4:  For tags from 0 to 30 the first octet is the identfier
    pg10: Hex 30 means sequence, followed by the length of that sequence.
    pg5:  Second octet is the length octet
          first bit indicates short or long form, next 7 bits encode the number
          of subsequent octets that make up the content length octets as an
          unsigned binary int

          82 = 10000010 (first bit indicates long form)
          0000010 = 2 octets of content length
          so read the next 2 octets to get the length of the content.

    In the case of a very large content length there could be a requirement to
    have more than 2 octets to designate the content length, therefore
    requiring us to check for MIM, MIQ, etc.
    In [4]: base64.b64encode(binascii.a2b_hex('3083'))
    Out[4]: 'MIM='
    In [5]: base64.b64encode(binascii.a2b_hex('3084'))
    Out[5]: 'MIQ='
    Checking for MI would become invalid at 16 octets of content length
    10010000 = 90
    In [6]: base64.b64encode(binascii.a2b_hex('3090'))
    Out[6]: 'MJA='
    Checking for just M is insufficient

    But we will only check for MII:
    Max length of the content using 2 octets is 7FFF or 32767
    It's not practical to support a token of this length or greater in http
    therefore, we will check for MII only and ignore the case of larger tokens
    """
    return token[:3] == PKI_ANS1_PREFIX


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
    return cms_pem_to_token_id(output)


def cms_hash_token(token_id):
    """Hash PKI tokens.

    return: for ans1_token, returns the hash of the passed in token
            otherwise, returns what it was passed in.
    """
    if token_id is None:
        return None
    if is_ans1_token(token_id):
        hasher = hashlib.md5()
        hasher.update(token_id)
        return hasher.hexdigest()
    else:
        return token_id
