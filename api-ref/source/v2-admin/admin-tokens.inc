.. -*- rst -*-

======
Tokens
======


List endoints for token
=======================

.. rest_method::  GET /v2.0/tokens/{tokenId}/endpoints

Lists the endpoints associated with a token.

Normal response codes: 200,203
Error response codes: 413,405,404,403,401,400,503

Request
-------

.. rest_parameters:: parameters.yaml

   - tokenId: token_id_path

Response Example
----------------

.. literalinclude:: samples/admin/token-endpoints-list-response.json
   :language: javascript


Authenticate for admin API
==========================

.. rest_method::  POST /v2.0/tokens

Authenticates and generates a token.

A REST interface provides client authentication by using the POST
method with ``v2.0/tokens`` as the path. Include a payload of
credentials in the body.

The Identity API is a RESTful web service. It is the entry point to
all service APIs. To access the Identity API, you must know its
URL.

Each REST request against the Identity Service requires the ``X
-Auth-Token`` header. Clients obtain this token and the URL
endpoints for other service APIs by supplying their valid
credentials to the authentication service.

If the authentication token has expired, this call returns the HTTP
``unauthorized (401)`` response code.

If the token has expired, this call returns the ``itemNotFound
(404)`` response code.

The Identity API treats expired tokens as no longer valid tokens.

The deployment determines how long expired tokens are stored.

To view the ``trust`` object, you need to set ``trust`` enable on
the keystone configuration.

Normal response codes: 200,203
Error response codes: 413,405,404,403,401,400,503

Request Example
---------------

.. literalinclude:: ../v2/samples/admin/authenticate-token-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - access: access
   - token: token
   - issued_at: token_issued_at
   - expires: token_expires
   - id: token_id
   - tenant: tenant
   - name: tenant_name
   - enabled: tenant_enabled
   - description: tenant_description
   - id: tenant_id
   - serviceCatalog: serviceCatalog
   - endpoints: endpoints
   - id: endpoint_id
   - adminURL: endpoint_adminurl_response
   - internalURL: endpoint_internalurl_response
   - publicURL: endpoint_publicurl_response
   - endpoints_links: endpoints_links
   - type: endpoint_type
   - name: endpoint_name
   - user: user
   - name: user_name
   - id: user_id
   - roles: roles
   - name: role_name
   - roles_links: roles_links
   - metadata: metadata
   - is_admin: metadata_is_admin
   - roles: metadata_roles
   - trust: trust
   - id: trust_id
   - impersonation: trust_impersonation
   - trustee_user_id: trust_trustee_user_id
   - trustor_user_id: trust_trustor_user_id

Response Example
----------------

.. literalinclude:: ../v2/samples/admin/authenticate-response.json
   :language: javascript


Validate token
==============

.. rest_method::  GET /v2.0/tokens/{tokenId}

Validates a token and confirms that it belongs to a tenant.

Returns the permissions relevant to a particular client. Valid
tokens are in the ``/tokens/{tokenId}`` path. If the token is not
valid, this call returns the ``itemNotFound (404)`` response code.

Normal response codes: 200,203
Error response codes: 413,405,404,403,401,400,503

Request
-------

.. rest_parameters:: parameters.yaml

   - tokenId: token_id_path

Response Example
----------------

.. literalinclude:: samples/admin/token-validate-response.json
   :language: javascript


Validate token (admin)
======================

.. rest_method::  HEAD /v2.0/tokens/{tokenId}

Validates a token and confirms that it belongs to a tenant, for performance.

Normal response codes: 200,203,204
Error response codes: 413,405,404,403,401,400,503

Request
-------

.. rest_parameters:: parameters.yaml

   - tokenId: token_id_path


Delete token
============

.. rest_method::  DELETE /v2.0/tokens/{tokenId}

Deletes a token.

Normal response codes: 204
Error response codes: 413,405,404,403,401,400,503

Request
-------

.. rest_parameters:: parameters.yaml

   - tokenId: token_id_path
