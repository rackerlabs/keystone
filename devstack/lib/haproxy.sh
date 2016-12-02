#!/bin/bash
#
# Copyright 2016: Mirantis Inc.
# All Rights Reserved.
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

KEYSTONE_PUBLIC_FRONTEND_PORT=${KEYSTONE_PUBLIC_FRONTEND_PORT:-13000}
KEYSTONE_ADMIN_FRONTEND_PORT=${KEYSTONE_ADMIN_FRONTEND_PORT:-13357}
HAPROXY_HOST=${HAPROXY_HOST:-$SERVICE_HOST}

HAPROXY_PUBLIC_FRONTEND="http://$HAPROXY_HOST:$KEYSTONE_PUBLIC_FRONTEND_PORT"
HAPROXY_ADMIN_FRONTEND="http://$HAPROXY_HOST:$KEYSTONE_ADMIN_FRONTEND_PORT"

AUTH_URI="${HAPROXY_PUBLIC_FRONTEND}"
AUTH_URL="${HAPROXY_ADMIN_FRONTEND}"

function configure_haproxy {

    haproxy_conf="/etc/haproxy/haproxy.cfg"
    haproxy_default_settings="/etc/default/haproxy"

    fernet_keys=$KEYSTONE_CONF_DIR/fernet-keys
    credential_keys=$KEYSTONE_CONF_DIR/credential-keys

    if [[ "$HAPROXY_HOST" == "$HOST_IP" ]]; then
        # On HAProxy server node:
        # At first we need to install HAProxy.
        install_package haproxy
        sudo chown -R stack $haproxy_default_settings
        sudo chmod 700 $haproxy_default_settings
        echo "ENABLED=1" > $haproxy_default_settings

        # Configure single HAProxy forntend for multiple Keystone services on
        # different machines. HAProxy frontend host and port should be used in
        # authentication urls in order to spread queries between multiple backend
        # keystone services.
        # We will define Keystone servers in 'host:port' way since HAProxy doesn't
        # support 'host/identity' ('host/identity_admin') syntax.

        sudo chown -R stack /etc/haproxy
        sudo chmod 700 /etc/haproxy

        cat <<EOF >> $haproxy_conf

frontend keystone-public-front
        bind ${HAPROXY_HOST}:${KEYSTONE_PUBLIC_FRONTEND_PORT}
        default_backend keystone-public-back
backend keystone-public-back
        balance roundrobin
        server controller ${SERVICE_HOST}:${KEYSTONE_SERVICE_PORT} check

frontend keystone-admin-front
        bind ${HAPROXY_HOST}:${KEYSTONE_ADMIN_FRONTEND_PORT}
        default_backend keystone-admin-back
backend keystone-admin-back
        balance roundrobin
        server controller ${SERVICE_HOST}:${KEYSTONE_AUTH_PORT} check

EOF
        start_service haproxy
    elif is_keystone_enabled && [[ "$HOST_IP" != "$SERVICE_HOST" ]]; then

        # After HAProxy was successfully installed and configured,
        # on Keystone node we need to add information about running
        # Keystone backend to HAProxy config which is stored on the
        # HAProxy server.
        install_package sshpass
        for port in $KEYSTONE_AUTH_PORT $KEYSTONE_SERVICE_PORT
        do
            conf_line="server keystone ${HOST_IP}:${port} check"
            sshpass -p "stack" ssh -o StrictHostKeyChecking=no stack@$HAPROXY_HOST \
                "sed -i '/.*controller.*:${port}.*/a \\\t${conf_line}' ${haproxy_conf}"
        done
        # For HA Keystone we need to share keys between Keystone nodes.
        sshpass -p "stack" ssh stack@$SERVICE_HOST \
            test -d $fernet_keys && scp -r stack@$SERVICE_HOST:$fernet_keys $KEYSTONE_CONF_DIR
        sshpass -p "stack" ssh stack@$SERVICE_HOST \
            test -d $credential_keys && scp -r stack@$SERVICE_HOST:$credential_keys $KEYSTONE_CONF_DIR

        # Restart HAProxy on the server.
        sshpass -p "stack" ssh stack@$HAPROXY_HOST \
            "sudo /bin/systemctl restart haproxy || sudo service haproxy restart"
    fi
}

function update_keystone_endpoints {
    if [[ "$SERVICE_HOST" == "$HOST_IP" ]]; then
        for interface in internal public
        do
            public_endpoint_id=$(openstack endpoint list --service keystone --interface $interface -c ID -f value)
            openstack endpoint set --url $AUTH_URI $public_endpoint_id
        done
        admin_endpoint_id=$(openstack endpoint list --service keystone --interface admin -c ID -f value)
        openstack endpoint set --url $AUTH_URL $admin_endpoint_id

        if [[ "$HAPROXY_HOST" == "$HOST_IP" ]]; then
            restart_service haproxy
        else
            sshpass -p "stack" ssh stack@$HAPROXY_HOST \
                "sudo /bin/systemctl restart haproxy || sudo service haproxy restart"
        fi
    fi
}

function configure_keystone_for_haproxy {
    if is_keystone_enabled; then
        iniset /etc/keystone/keystone.conf DEFAULT admin_endpoint $AUTH_URL
        iniset /etc/keystone/keystone.conf DEFAULT public_endpoint $AUTH_URI

        # This is a workaround to avoid failure of Tempest test
        # tempest.api.identity.admin.v3.test_roles.RolesV3TestJSON.test_role_create_update_show_list
        iniset /etc/keystone/keystone.conf cache enabled False
        restart_service apache2
    fi
}

function configure_services {
    if is_service_enabled n-api; then
        iniset /etc/nova/nova.conf keystone_authtoken auth_uri $AUTH_URI
        iniset /etc/nova/nova.conf keystone_authtoken auth_url $AUTH_URL
        iniset /etc/nova/nova-dhcpbridge.conf keystone_authtoken auth_uri $AUTH_URI
        iniset /etc/nova/nova-dhcpbridge.conf keystone_authtoken auth_url $AUTH_URL
    fi
    if is_cinder_enabled; then
        iniset /etc/cinder/cinder.conf keystone_authtoken auth_uri $AUTH_URI
        iniset /etc/cinder/cinder.conf keystone_authtoken auth_url $AUTH_URL
    fi
    if is_service_enabled neutron; then
        iniset /etc/nova/nova.conf neutron auth_url $AUTH_URL/v3
        iniset /etc/neutron/neutron.conf keystone_authtoken auth_uri $AUTH_URI
        iniset /etc/neutron/neutron.conf keystone_authtoken auth_url $AUTH_URL
        iniset /etc/neutron/neutron.conf nova auth_url $AUTH_URL
        iniset /etc/neutron/neutron.conf nova auth_uri $AUTH_URI
    fi
    if is_service_enabled g-api n-api; then
        iniset /etc/glance/glance-api.conf keystone_authtoken auth_url $AUTH_URL
        iniset /etc/glance/glance-api.conf keystone_authtoken auth_uri $AUTH_URI
        iniset /etc/glance/glance-registry.conf keystone_authtoken auth_url $AUTH_URL
        iniset /etc/glance/glance-registry.conf keystone_authtoken auth_uri $AUTH_URI
        iniset /etc/glance/glance-cache.conf DEFAULT auth_url $AUTH_URL/v3
    fi
    if is_swift_enabled; then
        iniset /etc/swift/proxy-server.conf "filter:authtoken" auth_uri $AUTH_URI
        iniset /etc/swift/proxy-server.conf "filter:authtoken" auth_url $AUTH_URL
    fi
    if is_ceilometer_enabled; then
        iniset /etc/ceilometer/ceilometer.conf service_credentials auth_url $AUTH_URI
        iniset /etc/ceilometer/ceilometer.conf keystone_authtoken auth_uri $AUTH_URI
        iniset /etc/ceilometer/ceilometer.conf keystone_authtoken auth_url $AUTH_URL
    fi
}

function configure_tempest_for_multi_keystone {
    if is_service_enabled tempest; then
        iniset $TEMPEST_CONFIG identity uri $AUTH_URI/v2.0
        iniset $TEMPEST_CONFIG identity uri_v3 $AUTH_URI/v3
    fi
}

function stop_haproxy {
    if [[ "$HOST_IP" == "$HAPROXY_HOST" ]]; then
        stop_service haproxy
    fi
}

function remove_haproxy {
    if [[ "$HOST_IP" == "$HAPROXY_HOST" ]]; then
        uninstall_package haproxy
    fi
}
