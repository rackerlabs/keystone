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

HAPROXY_CONF="/etc/haproxy/haproxy.cfg"
HAPROXY_DEFAULT_SETTINGS="/etc/default/haproxy"
KEYSTONE_FRONTEND_PORT=${KEYSTONE_FRONTEND_PORT:-5001}

function configure_haproxy {
    if [[ "$SERVICE_HOST" == "$HOST_IP" ]]; then
        # On Controller node:
        # At first we need to install and enable HAProxy.
        sudo apt-get install -y -q haproxy
        sudo chmod 777 $HAPROXY_DEFAULT_SETTINGS
        echo "ENABLED=1" > $HAPROXY_DEFAULT_SETTINGS

        # Configure single HAProxy forntend for multiple Keystone services on
        # different machines. HAProxy frontend host and port should be used in
        # OS_AUTH_URL in order to spread queries between multiple backend keystone
        # services.
        sudo chmod 777 $HAPROXY_CONF
        cat <<EOF >> $HAPROXY_CONF
frontend keystone-service-front
    bind ${SERVICE_HOST}:${KEYSTONE_FRONTEND_PORT}
    default_backend keystone-service-back
backend keystone-service-back
    balance roundrobin
    server controller ${SERVICE_HOST}:5000 check port 5000 inter 12000 rise 1 fall 1
EOF
        sudo service haproxy start
    else
        # After controller was successfully deployed, on Keystone node we need to add
        # information about running Keystone backend to HAProxy conf.
        sudo apt-get install sshpass
        conf_line="server keystone ${HOST_IP}:5000 "
        conf_line+="check port 5000 inter 12000 rise 1 fall 1"
        echo $conf_line | sshpass -p "stack" \
            ssh -o StrictHostKeyChecking=no stack@$SERVICE_HOST "cat >> ${HAPROXY_CONF}"
        # After HAProxy config was edited, we need to restart service itsetf.
        sshpass -p "stack" ssh stack@$SERVICE_HOST \
            "sudo service haproxy restart"
    fi
}

function stop_haproxy {
    if [[ "$HOST_IP" == "$SERVICE_HOST" ]]; then
        sudo service haproxy stop
    fi
}

function remove_haproxy {
    if [[ "$HOST_IP" == "$SERVICE_HOST" ]]; then
        sudo apt-get purge -y -q --auto-remove haproxy
    fi
}

