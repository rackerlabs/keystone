#!/usr/bin/env bash

# Copyright 2015 NEC Corporation.  All rights reserved.
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

# Test to verify that the openstackclient is installed, if not exit
type openstack >/dev/null 2>&1 || {
    echo >&2 "openstackclient is not installed. Please install it to use this script. Aborting."
    exit 1
    }

CLOUD_ADMIN_PASSWORD=${CLOUD_ADMIN_PASSWORD:-password}
CLOUD_USER_PASSWORD=${CLOUD_USER_PASSWORD:-password}

KEYSTONE_CONF=${KEYSTONE_CONF:-etc/keystone.conf}
# Extract some info from Keystone's configuration file
if [[ -r "$KEYSTONE_CONF" ]]; then
    CONFIG_ADMIN_TOKEN=$(sed 's/[[:space:]]//g' $KEYSTONE_CONF | grep ^admin_token= | cut -d'=' -f2)
    if [[ -z "${CONFIG_ADMIN_TOKEN}" ]]; then
        # default config options are commented out, so lets try those
        CONFIG_ADMIN_TOKEN=$(sed 's/[[:space:]]//g' $KEYSTONE_CONF | grep ^\#admin_token= | cut -d'=' -f2)
    fi
fi

KEYSTONE_POLICY_FILE=${KEYSTONE_POLICY_FILE:-etc/policy.json}
KEYSTONE_V3CLOUD_SAMPLE_POLICY_FILE=${KEYSTONE_V3CLOUD_SAMPLE_POLICY_FILE:-etc/policy.v3cloudsample.json}

OS_TOKEN=${OS_TOKEN:-$CONFIG_ADMIN_TOKEN}
if [[ -z "$OS_TOKEN" ]]; then
    echo "No service token found."
    echo "Set OS_TOKEN manually from keystone.conf admin_token."
    exit 1
fi

# Public facing bits
KEYSTONE_HOST=${KEYSTONE_HOST:-localhost}
KEYSTONE_ADMIN_PORT=${KEYSTONE_ADMIN_PORT:-35357}
KEYSTONE_PUBLIC_PORT=${KEYSTONE_PUBLIC_PORT:-5000}

ADMIN_URL=${OS_URL:-http://$KEYSTONE_HOST:${KEYSTONE_ADMIN_PORT}/v3}
PUBLIC_URL=${OS_URL:-http://$KEYSTONE_HOST:${KEYSTONE_PUBLIC_PORT}/v3}

# v3cloudsample
# Domain               User          Roles
# ------------------------------------------------------------------
# admin_domain         cloud_admin   admin
# dom1                 adm1          admin
# dom2                 adm2          admin

# exports variables
export OS_TOKEN=$OS_TOKEN
export OS_URL=$PUBLIC_URL
export OS_IDENTITY_API_VERSION=3

## admin domain
# create admin_domain
openstack domain create "admin_domain"

# create cloud_admin
openstack user create "cloud_admin" --password $CLOUD_ADMIN_PASSWORD --domain "admin_domain"

# create role admin
openstack role create "admin"

# admin role add to admin_domain/cloud_admin
openstack role add --domain "admin_domain" --user "cloud_admin" admin

admin_domain_id=$(openstack domain show "admin_domain" -f value | awk NR==2)

sed s/admin_domain_id/$admin_domain_id/ < $KEYSTONE_V3CLOUD_SAMPLE_POLICY_FILE > $KEYSTONE_POLICY_FILE

## dom1 domain
# create domain
openstack domain create "dom1"

# create user
openstack user create "adm1" --password $CLOUD_USER_PASSWORD --domain "dom1"

# create role
openstack role add --domain "dom1" --user "adm1" admin


## dom1 domain
# create domain
openstack domain create "dom2"

# create user
openstack user create "adm2" --password $CLOUD_USER_PASSWORD --domain "dom2"

# create role
openstack role add --domain "dom2" --user "adm2" admin

## service create
openstack service create --name keystone identity

## endpoint create
openstack endpoint create identity admin $ADMIN_URL
openstack endpoint create identity  public $PUBLIC_URL
openstack endpoint create identity internal $PUBLIC_URL

