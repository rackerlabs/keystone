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

# For more information on Devstack plugins, including a more detailed
# explanation on when the different steps are executed please see:
# http://docs.openstack.org/developer/devstack/plugins.html
HAPROXY_CONF="/etc/haproxy/haproxy.cfg"
HAPROXY_DEFAULT_SETTINGS="/etc/default/haproxy"
KEYSTONE_FRONTEND_PORT=${KEYSTONE_FRONTEND_PORT:-5001}
FERNET_KEYS="/etc/keystone/fernet-keys"

if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
    # This phase is executed after the projects have been installed
    echo "Keystone plugin - Pre-Install phase"
    if [[ "$MULTI_KEYSTONE" -eq "1" ]]; then
        if [[ "$HOST_IP" != "$SERVICE_HOST" ]]; then
            sed -i '/^MYSQL_HOST/d' $TOP_DIR/local.conf
        fi
    fi

elif [[ "$1" == "stack" && "$2" == "install" ]]; then
    # This phase is executed after the projects have been installed
    echo "Keystone plugin - Install phase"

elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    # This phase is executed after the projects have been configured and
    # before they are started
    echo "Keystone plugin - Post-config phase"

elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    # This phase is executed after the projects have been started
    if [[ "$MULTI_KEYSTONE" -eq "1" ]]; then
        if [[ "$SERVICE_HOST" == "$HOST_IP" ]]; then
            sudo apt-get install -y -q haproxy
            sudo chmod 777 $HAPROXY_DEFAULT_SETTINGS
            echo "ENABLED=1" > $HAPROXY_DEFAULT_SETTINGS
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
            sudo apt-get install sshpass
            conf_line="server keystone ${HOST_IP}:5000 "
            conf_line+="check port 5000 inter 12000 rise 1 fall 1"
            echo $conf_line | sshpass -p "stack" \
                ssh stack@$SERVICE_HOST "cat >> ${HAPROXY_CONF}"
            sshpass -p "stack" ssh stack@$SERVICE_HOST \
                "sudo service haproxy restart"
            for i in {0..1}
            do
                sshpass -p "stack" \
                    scp stack@$SERVICE_HOST:$FERNET_KEYS/$i $FERNET_KEYS/$i
            done
            # Change database connection string
            sed -i -e "s/127.0.0.1/${SERVICE_HOST}/g" /etc/keystone/keystone.conf
            sudo service apache2 restart
        fi
    fi
    echo "Keystone plugin - Extra phase"
fi

if [[ "$1" == "unstack" ]]; then
    # Called by unstack.sh and clean.sh
    # Undo what was performed during the "post-config" and "extra" phases
    :
fi

if [[ "$1" == "clean" ]]; then
    # Called by clean.sh after the "unstack" phase
    # Undo what was performed during the "install" phase
    :
    if [[ "$MULTI_KEYSTONE" -eq "1" ]]; then
        if [[ "$HOST_IP" == "$SERVICE_HOST" ]]; then
            sudo service haproxy stop
            sudo apt-get purge -y -q --auto-remove haproxy
        fi
    fi
fi
