# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Common parameter types for validating a request reference."""

rfc3986_dec_octet = '25[0-5]|(?:2[0-4]|1?[0-9])?[0-9]'
rfc3986_ipv4_address = '(?:%(dec-octet)s\.){3}(?:%(dec-octet)s)' \
    % {'dec-octet': rfc3986_dec_octet}
rfc3986_h16 = '[0-9A-Fa-f]{1,4}'
rfc3986_ls32 = '(?:%(h16)s):(?:%(h16)s)|(?:%(IPv4address)s)' \
    % {'h16': rfc3986_h16, 'IPv4address': rfc3986_ipv4_address}
rfc3986_ipv6_address = '(?:(?:%(h16)s:){6}(?:%(ls32)s)|' \
    '::(?:%(h16)s:){5}(?:%(ls32)s)|' \
    '(?:%(h16)s)?::(?:%(h16)s:){4}(?:%(ls32)s)|' \
    '(?:(?:%(h16)s:)?%(h16)s)?::(?:%(h16)s:){3}(?:%(ls32)s)|' \
    '(?:(?:%(h16)s:){,2}%(h16)s)?::(?:%(h16)s:){2}(?:%(ls32)s)|' \
    '(?:(?:%(h16)s:){,3}%(h16)s)?::%(h16)s:(?:%(ls32)s)|' \
    '(?:(?:%(h16)s:){,4}%(h16)s)?::(?:%(ls32)s)|' \
    '(?:(?:%(h16)s:){,5}%(h16)s)?::%(h16)s|' \
    '(?:(?:%(h16)s:){,6}%(h16)s)?::)' \
    % {'h16': rfc3986_h16, 'ls32': rfc3986_ls32}
rfc6874_zone_id = '(?:[0-9A-Za-z\-._~]|%[0-9A-Za-z]{2}){1,}'

boolean = {
    'type': 'boolean',
    'enum': [True, False]
}

# NOTE(lbragstad): Be mindful of this pattern as it might require changes
# once this is used on user names, LDAP-based user names specifically since
# commas aren't allowed in the following pattern. Here we are only going to
# check the length of the name and ensure that it's a string. Right now we are
# not going to validate on a naming pattern for issues with
# internationalization.
name = {
    'type': 'string',
    'minLength': 1,
    'maxLength': 255
}

id_string = {
    'type': 'string',
    'minLength': 1,
    'maxLength': 64,
    # TODO(lbragstad): Find a way to make this configurable such that the end
    # user chooses how much control they want over id_strings with a regex
    'pattern': '^[a-zA-Z0-9-]+$'
}

description = {
    'type': 'string'
}

url = {
    'type': 'string',
    'minLength': 0,
    'maxLength': 225,
    # NOTE(lbragstad): Using a regular expression here instead of the
    # FormatChecker object that is built into jsonschema. The FormatChecker
    # can validate URI formats but it depends on rfc3987 to do that
    # validation, and rfc3987 is GPL licensed. For our purposes here we will
    # use a regex and not rely on rfc3987 to validate URIs.
    'pattern': ('^https?://'
                '(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)'
                '+[a-zA-Z]{2,6}\.?|'
                'localhost|'
                '%(IPv4address)s|'
                '\[%(IPv6address)s(?:%%25%(ZoneID)s)?\])'
                '(?::\d+)?'
                '(?:/?|[/?]\S+)$') % {'IPv4address': rfc3986_ipv4_address,
                                      'IPv6address': rfc3986_ipv6_address,
                                      'ZoneID': rfc6874_zone_id}
}

email = {
    'type': 'string',
    'format': 'email'
}
