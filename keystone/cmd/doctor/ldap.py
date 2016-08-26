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

from __future__ import print_function

import os
import re

from six.moves import configparser

import keystone.conf


CONF = keystone.conf.CONF


def symptom_LDAP_user_enabled_emulation_dn_ignored():
    """`[ldap] user_enabled_emulation_dn` is being ignored.

    There is no reason to set this value unless `keystone.conf [ldap]
    user_enabled_emulation` is also enabled.
    """
    return (
        not CONF.ldap.user_enabled_emulation
        and CONF.ldap.user_enabled_emulation_dn is not None)


def symptom_LDAP_user_enabled_emulation_use_group_config_ignored():
    """`[ldap] user_enabled_emulation_use_group_config` is being ignored.

    There is no reason to set this value unless `keystone.conf [ldap]
    user_enabled_emulation` is also enabled.
    """
    return (
        not CONF.ldap.user_enabled_emulation
        and CONF.ldap.user_enabled_emulation_use_group_config)


def symptom_LDAP_group_members_are_ids_disabled():
    """`[ldap] group_members_are_ids` is not enabled.

    Because you've set `keystone.conf [ldap] group_objectclass = posixGroup`,
    we would have also expected you to enable set `keystone.conf [ldap]
    group_members_are_ids` because we suspect you're using Open Directory,
    which would contain user ID's in a `posixGroup` rather than LDAP DNs, as
    other object classes typically would.
    """
    return (
        CONF.ldap.group_objectclass == 'posixGroup'
        and not CONF.ldap.group_members_are_ids)


def symptom_LDAP_domain_specific_configs():
    """`[identity] domain_specific_drivers_enabled` is set to true.

    If you have set
    `keystone.conf [identity] domain_specific_drivers_enabled = true`,
    then keystone expects you to have domain specific configuration
    files located in the directory specified by
    `keystone.conf [identity] domain_config_dir`.

    Error: The configuration directory specified either does not exist or
    contains incorrectly named files. The files located in the directory
    specified should be in the form of keystone.<domain_name>.conf.
    """
    if not CONF.identity.domain_specific_drivers_enabled:
        return False

    invalid_files = []
    filedir = CONF.identity.domain_config_dir
    if os.path.isdir(filedir):
        for filename in os.listdir(filedir):
            if not re.match('^keystone\..*?\.conf$', filename):
                invalid_files.append(filename)
        if invalid_files:
            invalid_str = ', '.join(invalid_files)
            print('Error: The following files are named incorrectly:\n'
                  '%s\nThey should match the pattern of '
                  'keystone.<domain_name>.conf' % invalid_str)
            return True
    else:
        print('Could not find directory %s' % filedir)
        return True

    return False


def symptom_LDAP_domain_specific_configs_formatted_correctly():
    """LDAP domain specific configuration files are not formatted correctly.

    If you have set
    `keystone.conf [identity] domain_specific_drivers_enabled = true`,
    then keystone expects you to have domain specific configuration
    files located in the directory specified by
    `keystone.conf [identity] domain_config_dir`.

    The files should be in the form of keystone.<domain_name>.conf and
    their contents should look something like this:

    [ldap]
    url = ldap://ldapservice.thecustomer.com
    query_scope = sub

    user_tree_dn = ou=Users,dc=openstack,dc=org
    user_objectclass = MyOrgPerson
    user_id_attribute = uid
    ...
    """
    filedir = CONF.identity.domain_config_dir
    # NOTE(gagehugo): If domain_specific_drivers_enabled = false or
    # the value set in domain_config_dir is nonexistant/invalid, then
    # there is no point in continuing with this check.
    # symptom_LDAP_domain_specific_configs will catch and report this issue.
    if (not CONF.identity.domain_specific_drivers_enabled or
            not os.path.isdir(filedir)):
            return False

    try:
        for filename in os.listdir(filedir):
            parser = configparser.ConfigParser()
            parser.read(os.path.join(filedir, filename))
    except configparser.Error as e:
        print(e)
        return True
    else:
        return False
