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

boolean = {
    'type': ['boolean', 'string'],
    'enum': [True, 'True', 'TRUE', 'true', '1',
             False, 'False', 'FALSE', 'false', '0']
}

hostname = {
    'type': 'string', 'minLength': 1, 'maxLength': 255,
    # NOTE(lbragstad): 'host' is defined in "services" table, and that
    # means a hostname. The hostname grammar in RFC952 does not allow for
    # underscores in hostnames. However, this schema allows them, because it
    # sometimes occurs in real systems.
    'pattern': '^[a-zA-Z0-9-._]*$'
}

hostname_or_ip_address = {
    # NOTE(lbragstad): Allow to specify hostname, ipv4 and ipv6.
    'type': 'string', 'maxLength': 255,
    'pattern': '^[a-zA-Z0-9-_.:]*$'
}

# NOTE(lbragstad): Be mindful of this pattern as it might require changes
# once this is used on user names, LDAP-based user names specifically since
# commas aren't allowed in the following pattern.
name = {
    'type': 'string', 'minLength': 1, 'maxLength': 255,
    # NOTE(lbragstad): Allow to some spaces in middle of name.
    'pattern': '^(?! )[a-zA-Z0-9. _-]+(?<! )$'
}

uuid = {
    'type': 'string',
    'maxLength': 32,
    'minLength': 32,
    'pattern': '^[a-f0-9]*$'
}

description = {
    'type': ['string', 'null']
}

url = {
    'type': 'string',
    'pattern': '^https?://'
               '(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
               'localhost|'
               '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
               '(?::\d+)?'
               '(?:/?|[/?]\S+)$'
}
