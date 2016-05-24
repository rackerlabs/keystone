#!/usr/bin/env bash
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

KEYSTONE_PLUGIN_FILES=$DEST/keystone/devstack/files

function install_idp {
    if is_ubuntu; then
        install_package xmlsec1
    elif is_fedora; then
        install_package xmlsec1-openssl
    fi

    pip_install pysaml2
}

function configure_idp {
    iniset $KEYSTONE_CONF saml certfile "/etc/keystone/ssl/certs/ca.pem"
    iniset $KEYSTONE_CONF saml keyfile "/etc/keystone/ssl/private/cakey.pem"
    iniset $KEYSTONE_CONF saml idp_entity_id "http://$HOST_IP:5000/v3/OS-FEDERATION/saml2/idp"
    iniset $KEYSTONE_CONF saml idp_sso_endpoint "http://$HOST_IP:5000/v3/OS-FEDERATION/saml2/sso"
    iniset $KEYSTONE_CONF saml idp_metadata_path "/etc/keystone/keystone_idp_metadata.xml"

    keystone-manage pki_setup
    keystone-manage saml_idp_metadata > /etc/keystone/keystone_idp_metadata.xml

    restart_apache_server
}

function install_sp {
    if is_ubuntu; then
        install_package libapache2-mod-shib2
    elif is_fedora; then
        sudo wget -o /etc/yum.repos.d/security\:shibboleth.repo
            http://download.opensuse.org/repositories/security://shibboleth/CentOS_7/security:shibboleth.repo
        install_package mod_ssl shibboleth
    fi
}

function configure_sp {
    if is_ubuntu; then
        sudo shib-keygen -f
    elif is_fedora; then
        sudo /etc/shibboleth/keygen.sh -f
    fi

    local keystone_apache_conf=$(apache_site_config_for keystone)
    sudo sed -i -e "
        /<VirtualHost \*:5000>/r $KEYSTONE_PLUGIN_FILES/apache_alias.txt
    " $keystone_apache_conf
    cat $KEYSTONE_PLUGIN_FILES/apache_shib.txt | sudo tee -a $keystone_apache_conf

    sudo cp $KEYSTONE_PLUGIN_FILES/attribute-map.xml /etc/shibboleth/attribute-map.xml
    sudo cp $KEYSTONE_PLUGIN_FILES/shibboleth2.xml /etc/shibboleth/shibboleth2.xml
    sudo sed -e "
        s|%IDP_REMOTE_ID%|$IDP_REMOTE_ID|g;
        s|%IDP_METADATA%|$IDP_METADATA|g;
    " -i /etc/shibboleth/shibboleth2.xml

    iniset $KEYSTONE_CONF auth methods "external,password,token,oauth1,saml2"
    iniset $KEYSTONE_CONF auth saml2 "keystone.auth.plugins.mapped.Mapped"

    if is_ubuntu; then
        sudo a2enmod shib2
    fi

    restart_apache_server
    restart_service shibd

    local federated_user=$(get_or_create_user federated_user)
    local federated_project=$(get_or_create_project federated_project)
    local federated_group=$(get_or_create_group federated_group default)
    local member_role=$(get_or_create_role member)

    openstack group add user $federated_group $federated_user
    openstack role add --project $federated_project --group $federated_group $member_role

    local mapping_file
    if [ "$FEDERATION_MAPPING" == k2k ]; then
        $mapping_file=$KEYSTONE_PLUGIN_FILES/mapping-k2k.json
    elif [ "$FEDERATION_MAPPING" == generic ]; then
        $mapping_file=$KEYSTONE_PLUGIN_FILES/mapping-generic.json
    else
        # If other value, use it as the path for the mapping
        $mapping_file=$FEDERATION_MAPPING
    fi

    openstack --os-identity-api-version 3 identity provider create \
        --remote-id $IDP_REMOTE_ID $IDP_ID
    openstack --os-identity-api-version 3 mapping create \
        --rules $mapping_file mapping1
    openstack --os-identity-api-version 3 federation protocol create \
        --identity-provider $IDP_ID --mapping mapping1 saml2
}

function uninstall_idp {
    if is_ubuntu; then
        uninstall_package xmlsec1
    elif is_fedora; then
        uninstall_package xmlsec1-openssl
    fi
}

function uninstall_sp {
    if is_ubuntu; then
        uninstall_package libapache2-mod-shib2
    elif is_fedora; then
        uninstall_package shibboleth mod_ssl
        sudo rm /etc/yum.repos.d/security\:shibboleth.repo
    fi
}

if [[ "$1" == "stack" && "$2" == "install" ]]; then
    if is_service_enabled k2k-idp; then
        install_idp
    fi

    if is_service_enabled federation-sp; then
        install_sp
    fi

elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    if is_service_enabled k2k-idp; then
        configure_idp
    fi

    if is_service_enabled federation-sp; then
        configure_sp
    fi

elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    :
fi

if [[ "$1" == "unstack" ]]; then
    :
fi

if [[ "$1" == "clean" ]]; then
    if is_service_enabled k2k-idp; then
        uninstall_idp
    fi

    if is_service_enabled federation-sp; then
        uninstall_sp
    fi
fi
