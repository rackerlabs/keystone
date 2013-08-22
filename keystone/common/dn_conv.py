# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
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

'''
Convert between OpenSSL's proprietary DN format and RFC-4514 format.

RFC-4514 "String Representation of Distinguished Names" defines how a
DN is converted between the ASN.1 encoding of a DN and its string
representation. RFC-4514 superceeds RFC-2253.

Terminology
-----------

Familiarity with the following terms is necessary:

    DN
        Distinguished Name, an ordered sequence of RDN's.
        In RFC-4514 format each RDN in the sequence is separated by
        the comma (,) character.
    RDN
        Relative Distinguished Name, an unordered set of AVA's. By far
        the most common form of an RDN is when its set of AVA's
        only contains one member, i.e. a single valued RDN,
        e.g. "cn=Bob".
    AVA
        Attribute Value Assertion, a <type,value> pair.
        The type is often thought of as a name but in fact it is an OID
        (Object Identifer), a registered sequence of integers uniquely
        identifying something. OID's often have short and long names
        associated with them. For example the OID for Common Name is
        2.5.4.3, its short name is "cn" and its long name is
        "commonName".  An AVA is written as "type=value", for example
        "cn=Bob".
    Multivalued RDN
        An RDN which has more than one AVA. When matching is performed
        on an RDN each AVA must match (i.e. conjunction). When an RDN
        has more than one AVA the AVA's are separated by a plus sign
        (+) as written in RFC-4514 format. For example this RDN has 2
        AVA's "ou=sales+cn=Bob".
    ASN.1
        A schema for representing complex data in binary form
        characterized by specific encoding and decoding rules. Often
        used in defining network protocols.

Overview
--------

In X509 DN's are used for the subject and issuer fields
of a certificate (X509 extensions also utilize DN's).

RFC-4514 specifies the string representation of a DN. The majority of
libraries implementing X509 and the PKI infrastructure follow RFC-4514
when they parse a string representation of a DN or when they emit a
string representation of a DN.

Example:
    "CN=user@example.com,L=Nashua,ST=New Hampshire,C=US"

OpenSSL is an exception, OpenSSL uses its own syntax for DN's when it
receives a DN in string format. It (sometimes) emits DN's in RFC format
but only if you specify the right flags in commands which accept them
(e.g. x509's -nameopt arg with the RFC2253 option which is not
the default). The most common place OpenSSL uses its unique DN syntax
is for specifying the subject and issuer fields of a X509 certificate.

The above RFC-4514 DN would be this in OpenSSL:

    "/C=US/ST=New Hampshire/L=Nashua/CN=user@example.com"

Normalization
-------------

We adopt the rule that all DN's will be represented in RFC-4514
format.

We need to be able to recognize when a DN is in OpenSSL format and be
able to convert between the OpenSSL format and the RFC-4514 format in
order to interoperate with different libraries.

Ordering of RDN's in a DN
-------------------------

In RFC-4514 Section 2.1. "Converting the RDNSequence" states that the
output consists of the string encodings of each RDN in the RDN
sequence starting with the last element of the sequence and moving
backwards toward the first.

Thus the string representation of a DN (i.e. RDN sequence) is in
reverse order to the ASN.1 binary representation.

OpenSSL DN Format
-----------------

OpenSSL uses the format "/type0=value0/type1=value1/type2=value2"
with the backslash (\) character used as an escape.

Example:
    "/C=US/ST=New Hampshire/L=Nashua/CN=user@example.com"

The AVA type is introduced by a slash (/) followed by the AVA type
name which is separated by an equal sign (=) and then followed by the
AVA value. Note there is no explict RDN separator as there is in RFC
4514.

OpenSSL's DN parsing function is parse_name() in the file apps/apps.c.

OpenSSL Multivalued RDN's
~~~~~~~~~~~~~~~~~~~~~~~~~

OpenSSL encodes multple AVA's in an RDN this way:

"/type0=value0+type1=value1"

The first AVA in the RDN utilizes the "/type=value" form. Subsequent
AVA's appear as "+type=value". In other words since there is no RDN
separator in OpenSSL you must split the RDN's in DN by dividing the DN
into a sequence of /type=value entities. Then within each value you
must further split on "+type=value" to locate additional AVA's inside
the RDN.

By default OpenSSL does not recognize multivalue RDN's. You must pass
an explicit flag to OpenSSL commands for it to treat a multivalue RDN
as multivalued, for example from the "openssl req" command
documentaton.

    -multivalue-rdn
        This option causes the -subj argument to be interpreted with
        full support for multivalued RDNs. Example:

        /DC=org/DC=OpenSSL/DC=users/UID=123456+CN=John Doe

       If -multivalue-rdn is not used then the UID value is
       123456+CN=John Doe.


OpenSSL Reversing Ordering
~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenSSL builds a DN by parsing the constituent RDN's and then
appending each RDN in the order it appeared in the string into its
ASN.1 struture. Thus OpenSSL's string representation of a DN appears
to have reversed order from the RFC-4514 form. Recall RFC-4514 orders
RDN's from the last to the first in the ASN.1 sequence.

Support Libraries
-----------------

Correctly parsing and formatting DN's is non-trival. There are
numerous formats for AVA types, quoting rules, etc. Where possible we
use the str2dn() and dn2str() functions from the ldap.dn module which
correctly covers all the edge cases. These functions use an
intermediate Python form.

A DN is a list of RDN's, each RDN is a list of AVA's, and each AVA is
a 3-tuple (type, value, flags). See the python-ldap documentation for
details.
'''

# Necessary to import top-level modules shadowed by subpackage, see PEP-328
from __future__ import absolute_import

import ldap
import re

#--------------------------------------------------------------------------
# Regular Expressions internally used by this module.
# Pre-compile for efficiency.
#
# Note, <descr> and <numericoid> are the lexical definitions for
# an AVA type, defined in RFC-2252


# Regular expression used to check if DN is OpenSSL format
# Must start with '/Identifer=', permit leading whitespace

_openssl_dn_re = re.compile(
    # optional leading whitespace
    r'^\s*'
    # unescaped slash (/)
    r'(?<!\\)/'
    # <desc> or <numericoid>
    r'(([a-zA-Z][a-zA-Z0-9-]*?)|([0-9][0-9.]*?))'
    # unescaped equal sign (=) with optional whitespace
    r'\s*(?<!\\)=\s*'
)

# OpenSSL RDN regular expression
#
# Search for text like '/CN=foo bar'
# CN is the AVA Type, always preceded by slash (/)
# Text after the equal sign (=) is the AVA Value

_openssl_rdn_re = re.compile(
    # unescaped slash (/)
    r'(?<!\\)/'
    # <desc> or <numericoid> (group 1: AVA Type Name)
    r'(([a-zA-Z][a-zA-Z0-9-]*?)|([0-9][0-9.]*?))'
    # unescaped equal sign (=) with optional whitespace
    r'\s*(?<!\\)=\s*'
    # everything until ... (group 4: AVA Value)
    r'(.+?)'
    # next AVA or end of string
    r'(('
    r'(?<!\\)/(([a-zA-Z][a-zA-Z0-9-]*?)|([0-9][0-9.]*?))'
    r')|$)'
)

# OpenSSL multivalued RDN regular expression
# for AVA's following the initial AVA
#
# Search for text like '+CN=foo bar'
# CN is the AVA Type, always preceded by plus sign (+0
# Text after the equal sign (=) is the AVA Value

_openssl_multivalue_rdn_re = re.compile(
    # unescaped plus sign (+)
    r'(?<!\\)\+'
    # <desc> or <numericoid> (group 1: AVA Type Name)
    r'(([a-zA-Z][a-zA-Z0-9-]*?)|([0-9][0-9.]*?))'
    # unescaped equal sign (=) with optional whitespace
    r'\s*(?<!\\)=\s*'
    # everything until ... (group 4: AVA Value)
    r'(.+?)'
    # next AVA or end of string
    r'(('
    r'(?<!\\)\+(([a-zA-Z][a-zA-Z0-9-]*?)|([0-9][0-9.]*?))'
    r')|$)'
)

#--------------------------------------------------------------------------


def is_openssl_dn(dn):
    '''Tests if DN is in OpenSSL format

    :param string dn: DN to evaluate.
    :returns: boolean, True if OpenSSL format, False otherwise
    '''

    if _openssl_dn_re.search(dn) is None:
        return False
    else:
        return True


def is_rfc_dn(dn):
    '''Tests if DN is in RFC-4514 format

    :param string dn: DN to evaluate.
    :returns: boolean, True if RFC format, False otherwise
    '''

    try:
        rdns = ldap.dn.str2dn(dn)
    except ldap.DECODING_ERROR:
        return False
    else:
        # ldap.dn.str2dn permits an empty string, it returns an empty
        # list, however we demand dn's to be non-empty.
        if len(rdns) > 0:
            return True
        else:
            return False


def rfc_dn_to_openssl_dn(rfc_dn, reverse=True):
    '''Convert RFC-4514 formatted DN to OpenSSL DN format

    :param string rfc_dn: String DN in RFC-4514 format
    :param boolean reverse: Orders RDN's in the reverse from RFC-4514,
                            this is the OpenSSL default.
    :return: String DN in OpenSSL format.
    :raises: ValueError if input DN is invalid.
    '''
    try:
        rdns = ldap.dn.str2dn(rfc_dn)
    except ldap.DECODING_ERROR:
        raise ValueError('invalid dn "%s"' % (rfc_dn))

    openssl_rdns = []
    for rdn in rdns:
        if reverse:
            # The order of AVA's in a multivalued RDN are not
            # significant because the AVA's are considered a set
            # (i.e. unordered collection). When generating a printed
            # representation OpenSSL reverses the sequence of AVA's.
            # We also reverse the AVA's to be compatible with OpenSSL
            # to avoid confusion.
            rdn.reverse()
        ava = rdn[0]
        openssl_rdn = '/%s=%s' % (ava[0], ava[1])

        # The 2nd and subsequent AVA's use the "+type" notation.
        for ava in rdn[1:]:
            openssl_rdn += '+%s=%s' % (ava[0], ava[1])
        openssl_rdns.append(openssl_rdn)

    if reverse:
        openssl_rdns.reverse()
    openssl_dn = ''.join(openssl_rdns)
    return openssl_dn


def openssl_dn_to_rfc_dn(openssl_dn, multivalue_rdn=False):
    '''Convert OpenSSL formatted DN to RFC-4514 DN format

    :param string openssl_dn: String DN in OpenSSL format.
    :param bool multivalue_rdn: If true treat each RDN as potentially
                                multivalued. Otherwise multivalue syntax
                                inside an AVA value will not be recognized.
                                OpenSSL defaults to False.
    :return: String DN in RFC-4514 format.
    :raises: ValueError if not OpenSSL formatted DN
    '''

    if not is_openssl_dn(openssl_dn):
        raise ValueError('not an OpenSSL formatted DN "%s"' % openssl_dn)

    flags = 1
    rdns = []
    start = 0
    while True:
        # Split into /type=value entities Note, we can't use
        # re.finditer() because the regexp includes the next
        # /type=value, that's how we know we've reached the end of the
        # current value, so instead of finditer() we utilize start/end
        # positions.
        match = _openssl_rdn_re.search(openssl_dn, pos=start)
        if match is None:
            break
        first_ava_type = match.group(1)
        first_ava_value = match.group(4)
        start = match.end(4)
        avas = []
        if multivalue_rdn:
            # Does this value contain any +type=value constructs?
            # If so everything preceding the first +type=value is the
            # value of the first AVA.

            subsequent_start = 0
            first = True

            # in case no subsequent AVA's are found
            first_value = first_ava_value

            while True:
                # Scan for +type=value, the same issue with respect to
                # finditer() applies here as well.
                match = _openssl_multivalue_rdn_re.search(first_ava_value,
                                                          pos=subsequent_start)
                if match is None:
                    break
                if first:
                    # If this is first +type=value then everything preceding
                    # it is the value for the first AVA
                    first_value = first_ava_value[0:match.start(1) - 1]
                    first = False
                subsequent_ava_type = match.group(1)
                subsequent_ava_value = match.group(4)
                subsequent_start = match.end(4)
                avas.append((subsequent_ava_type, subsequent_ava_value, flags))

            # Insert the first AVA at the head of the RDN list
            avas.insert(0, ((first_ava_type, first_value, flags)))
            avas.reverse()
        else:
            # Not doing multivalue RDN's,
            # just include what we initially found
            avas.append((first_ava_type, first_ava_value, flags))
        rdns.append(avas)

    rdns.reverse()

    # Assemble the tokenized pieces back into an RFC-4514 form
    rfc_dn = ldap.dn.dn2str(rdns)

    return rfc_dn
