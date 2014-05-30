..
      Copyright 2011-2012 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=======================
API Examples using Curl
=======================

-------------------------------
v3 API Examples Using Curl
-------------------------------

Tokens
======

Unscoped
--------

Get an unscoped token::

    curl -i \
      -H "Content-Type: application/json" \
      -d '
    { "auth": {
        "identity": {
          "methods": ["password"],
          "password": {
            "user": {
              "name": "admin",
              "domain": { "id": "default" },
              "password": "adminpwd"
            }
          }
        }
      }
    }' \
      http://localhost:5000/v3/auth/tokens ; echo

Project-scoped
--------------

Get a project-scoped token::

    curl -i \
      -H "Content-Type: application/json" \
      -d '
    { "auth": {
        "identity": {
          "methods": ["password"],
          "password": {
            "user": {
              "name": "admin",
              "domain": { "id": "default" },
              "password": "adminpwd"
            }
          }
        },
        "scope": {
          "project": {
            "name": "demo",
            "domain": { "id": "default" }
          }
        }
      }
    }' \
      http://localhost:5000/v3/auth/tokens ; echo

Domain-Scoped
-------------

Get a domain-scoped token (Note that you're going to need a role on the domain
first!)::

    curl -i \
      -H "Content-Type: application/json" \
      -d '
    { "auth": {
        "identity": {
          "methods": ["password"],
          "password": {
            "user": {
              "name": "admin",
              "domain": { "id": "default" },
              "password": "adminpwd"
            }
          }
        },
        "scope": {
          "domain": {
            "id": "default"
          }
        }
      }
    }' \
      http://localhost:5000/v3/auth/tokens ; echo

Re-scoping
----------

Get a token from a token::

    curl -i \
      -H "Content-Type: application/json" \
      -d '
    { "auth": {
        "identity": {
          "methods": ["token"],
          "token": {
            "id": "'$TOKEN'"
          }
        }
      }
    }' \
      http://localhost:5000/v3/auth/tokens ; echo


DELETE /v3/auth/tokens
----------------------

Revoke a token::

    curl -i -X DELETE -H "X-Auth-Token: $TOKEN" -H "X-Subject-Token: $TOKEN" \
      http://localhost:5000/v3/auth/tokens


Projects
========

GET /v3/projects
----------------

List projects::

    curl \
     -H "X-Auth-Token: $TOKEN" \
     http://localhost:5000/v3/projects | python -mjson.tool

PATCH /v3/projects/{id}
-----------------------

Disable a project::

    curl -X PATCH \
      -H "X-Auth-Token: $TOKEN" \
      -H "Content-Type: application/json" \
      -d '
    {
      "project": {
          "enabled": false
        }
    }'\
      http://localhost:5000/v3/projects/$PROJECT_ID


GET /v3/services
================

List the services::

    curl -i \
      -H "X-Auth-Token: $TOKEN" \
      http://localhost:5000/v3/services


GET /v3/endpoints
=================

List the endpoints::

    curl \
     -H "X-Auth-Token: $TOKEN" \
     http://localhost:5000/v3/endpoints | python -mjson.tool


GET /v3/users
=============

List users::

    curl \
     -H "X-Auth-Token: $TOKEN" \
     http://localhost:5000/v3/users | python -mjson.tool


POST /v3/users/{user_id}/password
=================================

Change password::

    USER_ID=b7793000f8d84c79af4e215e9da78654
    ORIG_PASS=adminpwd
    NEW_PASS=newadminpwd

    curl -i \
     -H "X-Auth-Token: $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{ "user": {"password": "'$NEW_PASS'", "original_password": "'$ORIG_PASS'"} }' \
     http://localhost:5000/v3/users/$USER_ID/password


PUT /v3/projects/{project_id}/groups/{group_id}/roles/{role_id}
===============================================================

Create group role assignment on project::

    curl -i -X PUT \
     -H "X-Auth-Token: $TOKEN" \
     http://localhost:5000/v3/projects/$PROJECT_ID/groups/$GROUP_ID/roles/$ROLE_ID


POST /v3/OS-TRUST/trusts
========================

Create a trust::

    PROJECT_ID=ce4a76fa779a4f66b6e10e201fe00f11
    DEMO_USER_ID=60ec1f87a2624ca593695a0851f10db2
    ADMIN_USER_ID=97625786c6ef4976958c0fb5e8b17023

    curl \
     -H "X-Auth-Token: $TOKEN" \
     -H "Content-Type: application/json" \
     -d '
    { "trust": {
        "expires_at": "2014-12-30T23:59:59.999999Z",
        "impersonation": true,
        "project_id": "'$PROJECT_ID'",
        "roles": [
            { "name": "admin" }
          ],
        "trustee_user_id": "'$DEMO_USER_ID'",
        "trustor_user_id": "'$ADMIN_USER_ID'"
    }}'\
     http://localhost:5000/v3/OS-TRUST/trusts


-------------------------------
Service API Examples Using Curl
-------------------------------

The service API is defined to be a subset of the Admin API and, by
default, runs on port 5000.

GET /
=====

This call is identical to that documented for the Admin API, except
that it uses port 5000, instead of port 35357, by default::

    $ curl http://0.0.0.0:5000

or::

    $ curl http://0.0.0.0:5000/v2.0/

See the `Admin API Examples Using Curl`_ for more info.

GET /extensions
===============

This call is identical to that documented for the Admin API.

POST /tokens
============

This call is identical to that documented for the Admin API.

GET /tenants
============

List all of the tenants your token can access::

    $ curl -H "X-Auth-Token:887665443383838" http://localhost:5000/v2.0/tenants

Returns::

    {
        "tenants_links": [],
        "tenants": [
            {
                "enabled": true,
                "description": "None",
                "name": "customer-x",
                "id": "1"
            }
        ]
    }

-----------------------------
Admin API Examples Using Curl
-----------------------------

These examples assume a default port value of 35357, and depend on the
``sampledata`` bundled with keystone.

GET /
=====

Discover API version information, links to documentation (PDF, HTML, WADL),
and supported media types::

    $ curl http://0.0.0.0:35357

or::

    $ curl http://0.0.0.0:35357/v2.0/

Returns::

    {
        "version":{
            "id":"v2.0",
            "status":"beta",
            "updated":"2011-11-19T00:00:00Z",
            "links":[
                {
                    "rel":"self",
                    "href":"http://127.0.0.1:35357/v2.0/"
                },
                {
                    "rel":"describedby",
                    "type":"text/html",
                    "href":"http://docs.openstack.org/"
                },
            ],
            "media-types":[
                {
                    "base":"application/xml",
                    "type":"application/vnd.openstack.identity-v2.0+xml"
                },
                {
                    "base":"application/json",
                    "type":"application/vnd.openstack.identity-v2.0+json"
                }
            ]
        }
    }

GET /extensions
===============

Discover the API extensions enabled at the endpoint::

    $ curl http://localhost:35357/v2.0/extensions/

Returns::

    {
        "extensions":{
            "values":[]
        }
    }

POST /tokens
============

Authenticate by exchanging credentials for an access token::

    $ curl -d '{"auth":{"tenantName": "customer-x", "passwordCredentials": {"username": "joeuser", "password": "secrete"}}}' -H "Content-type: application/json" http://localhost:35357/v2.0/tokens

Returns::

    {
        "access":{
            "token":{
                "expires":"2012-02-05T00:00:00",
                "id":"887665443383838",
                "tenant":{
                    "id":"1",
                    "name":"customer-x"
                }
            },
            "serviceCatalog":[
                {
                    "endpoints":[
                    {
                        "adminURL":"http://swift.admin-nets.local:8080/",
                        "region":"RegionOne",
                        "internalURL":"http://127.0.0.1:8080/v1/AUTH_1",
                        "publicURL":"http://swift.publicinternets.com/v1/AUTH_1"
                    }
                    ],
                    "type":"object-store",
                    "name":"swift"
                },
                {
                    "endpoints":[
                    {
                        "adminURL":"http://cdn.admin-nets.local/v1.1/1",
                        "region":"RegionOne",
                        "internalURL":"http://127.0.0.1:7777/v1.1/1",
                        "publicURL":"http://cdn.publicinternets.com/v1.1/1"
                    }
                    ],
                    "type":"object-store",
                    "name":"cdn"
                }
            ],
            "user":{
                "id":"1",
                "roles":[
                    {
                    "tenantId":"1",
                    "id":"3",
                    "name":"Member"
                    }
                ],
                "name":"joeuser"
            }
        }
    }

.. note::

    Take note of the value ['access']['token']['id'] value produced here (``887665443383838``, above), as you can use it in the calls below.

GET /tokens/{token_id}
======================

.. note::

    This call refers to a token known to be valid, ``887665443383838`` in this case.

Validate a token::

    $ curl -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/tokens/887665443383838

If the token is valid, returns::

    {
        "access":{
            "token":{
                "expires":"2012-02-05T00:00:00",
                "id":"887665443383838",
                "tenant":{
                    "id":"1",
                    "name":"customer-x"
                }
            },
            "user":{
                "name":"joeuser",
                "tenantName":"customer-x",
                "id":"1",
                "roles":[
                    {
                        "serviceId":"1",
                        "id":"3",
                        "name":"Member"
                    }
                ],
                "tenantId":"1"
            }
        }
    }

HEAD /tokens/{token_id}
=======================

This is a high-performance variant of the GET call documented above, which
by definition, returns no response body::

    $ curl -I -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/tokens/887665443383838

... which returns ``200``, indicating the token is valid::

    HTTP/1.1 200 OK
    Content-Length: 0
    Content-Type: None
    Date: Tue, 08 Nov 2011 23:07:44 GMT

GET /tokens/{token_id}/endpoints
================================

List all endpoints for a token::

    $ curl -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/tokens/887665443383838/endpoints

Returns::

    {
        "endpoints_links": [
            {
                "href": "http://127.0.0.1:35357/tokens/887665443383838/endpoints?'marker=5&limit=10'",
                "rel": "next"
            }
        ],
        "endpoints": [
            {
                "internalURL": "http://127.0.0.1:8080/v1/AUTH_1",
                "name": "swift",
                "adminURL": "http://swift.admin-nets.local:8080/",
                "region": "RegionOne",
                "tenantId": 1,
                "type": "object-store",
                "id": 1,
                "publicURL": "http://swift.publicinternets.com/v1/AUTH_1"
            },
            {
                "internalURL": "http://localhost:8774/v1.0",
                "name": "nova_compat",
                "adminURL": "http://127.0.0.1:8774/v1.0",
                "region": "RegionOne",
                "tenantId": 1,
                "type": "compute",
                "id": 2,
                "publicURL": "http://nova.publicinternets.com/v1.0/"
            },
            {
                "internalURL": "http://localhost:8774/v1.1",
                "name": "nova",
                "adminURL": "http://127.0.0.1:8774/v1.1",
                "region": "RegionOne",
                "tenantId": 1,
                "type": "compute",
                "id": 3,
                "publicURL": "http://nova.publicinternets.com/v1.1/
            },
            {
                "internalURL": "http://127.0.0.1:9292/v1.1/",
                "name": "glance",
                "adminURL": "http://nova.admin-nets.local/v1.1/",
                "region": "RegionOne",
                "tenantId": 1,
                "type": "image",
                "id": 4,
                "publicURL": "http://glance.publicinternets.com/v1.1/"
            },
            {
                "internalURL": "http://127.0.0.1:7777/v1.1/1",
                "name": "cdn",
                "adminURL": "http://cdn.admin-nets.local/v1.1/1",
                "region": "RegionOne",
                "tenantId": 1,
                "type": "object-store",
                "id": 5,
                "publicURL": "http://cdn.publicinternets.com/v1.1/1"
            }
        ]
    }

GET /tenants
============

List all of the tenants in the system (requires an Admin ``X-Auth-Token``)::

    $ curl -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/tenants

Returns::

    {
        "tenants_links": [],
        "tenants": [
            {
                "enabled": false,
                "description": "None",
                "name": "project-y",
                "id": "3"
            },
            {
                "enabled": true,
                "description": "None",
                "name": "ANOTHER:TENANT",
                "id": "2"
            },
            {
                "enabled": true,
                "description": "None",
                "name": "customer-x",
                "id": "1"
            }
        ]
    }

GET /tenants/{tenant_id}
========================

Retrieve information about a tenant, by tenant ID::

    $ curl -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/tenants/1

Returns::

    {
        "tenant":{
            "enabled":true,
            "description":"None",
            "name":"customer-x",
            "id":"1"
        }
    }

GET /tenants/{tenant_id}/users/{user_id}/roles
==============================================

List the roles a user has been granted on a tenant::

    $ curl -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/tenants/1/users/1/roles

Returns::

    {
        "roles_links":[],
        "roles":[
            {
                "id":"3",
                "name":"Member"
            }
        ]
    }

GET /users/{user_id}
====================

Retrieve information about a user, by user ID::

    $ curl -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/users/1

Returns::

    {
        "user":{
            "tenantId":"1",
            "enabled":true,
            "id":"1",
            "name":"joeuser"
        }
    }

GET /users/{user_id}/roles
==========================

Retrieve the roles granted to a user, given a user ID::

    $ curl -H "X-Auth-Token:999888777666" http://localhost:35357/v2.0/users/4/roles

Returns::

    {
        "roles_links":[],
        "roles":[
            {
                "id":"2",
                "name":"KeystoneServiceAdmin"
            }
        ]
    }

GET /tokens/revoked
===================

Get the revocation list::

    curl -s -H "X-Auth-Token: adminpwd" \
      http://localhost:35357/v2.0/tokens/revoked |
     jq -r .signed |
     openssl cms -verify \
      -certfile /etc/keystone/ssl/certs/signing_cert.pem \
      -CAfile /etc/keystone/ssl/certs/ca.pem \
      -inform PEM \
      -nosmimecap -nodetach -nocerts -noattr 2>/dev/null |
     python -m json.tool
