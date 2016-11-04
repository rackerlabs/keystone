# Copyright 2016 Massachusetts Open Cloud
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

function install_federation {
    if is_ubuntu; then
        install_package libapache2-mod-shib2

        sudo shib-keygen -f
        sudo a2enmod shib2
    else
        # Note(knikolla): For CentOS/RHEL, installing shibboleth is tricky.
        # It requires adding a separate repo not officially supported.
        echo "Skipping installation of shibboleth for non ubuntu host"
    fi
}

function configure_federation {
    local keystone_apache_conf=$(apache_site_config_for keystone)

    # Add WSGIScriptAliasMatch to the VirtualHost for :5000
    sudo sed -i -e "
        /<VirtualHost \*:5000>/r $KEYSTONE_PLUGIN/files/federation/shib_apache_alias.txt
    " $keystone_apache_conf

    # Append the apache configuration
    cat $KEYSTONE_PLUGIN/files/federation/shib_apache_handler.txt | sudo tee -a $keystone_apache_conf

    # Copy a shibboleth2.xml configuration which is already configured for testshib.org
    sudo cp $KEYSTONE_PLUGIN/files/federation/shibboleth2.xml /etc/shibboleth/shibboleth2.xml

    iniset $KEYSTONE_CONF auth methods "external,password,token,mapped"
}

function register_federation {
    local federated_domain=$(get_or_create_domain federated_domain)
    local federated_project=$(get_or_create_project federated_project federated_domain)
    local federated_users=$(get_or_create_group federated_users)
    local member_role=$(get_or_create_role Member)

    openstack role add --group $federated_users --domain $federated_domain $member_role
    openstack role add --group $federated_users --project $federated_project $member_role

    openstack --os-identity-api-version 3 identity provider create testshib \
        --remote-id https://idp.testshib.org/idp/shibboleth

    openstack --os-identity-api-version 3 federation protocol create mapped \
        --mapping $KEYSTONE_PLUGIN/files/federation/mapping.json \
        --identity-provider testshib
}
