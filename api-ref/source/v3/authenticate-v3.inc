.. -*- rst -*-

=====================================
 Authentication and token management
=====================================

The Identity service generates tokens in exchange for authentication
credentials. A token represents the authenticated identity of a user and,
optionally, grants authorization on a specific project, domain, or the
deployment system.

The body of an authentication request must include a payload that
specifies the authentication method, which is ``password`` or
``token``, the credentials, and, optionally, the authorization
scope. You can scope a token to a project, domain, the deployment system, or
the token can be unscoped. You cannot scope a token to multiple scope targets.

Tokens have IDs, which the Identity API returns in the
``X-Subject-Token`` response header.

After you obtain an authentication token, you can:

- Make REST API requests to other OpenStack services. You supply the
  ID of your authentication token in the ``X-Auth-Token`` request
  header.

- Validate your authentication token and list the domains, projects,
  roles, and endpoints that your token gives you access to.

- Use your token to request another token scoped for a different
  domain and project.

- Force the immediate revocation of a token.

- List revoked public key infrastructure (PKI) tokens.

In v3.7 of the Identity API service, two new configuration options
were added: ``[resource] admin_project_name`` and
``[resource] admin_project_domain_name``. The options represent the
project that only the cloud administrator should be able to access.
When an authentication request for a token scoped to the admin project
is processed, it will have an additional field in the token
``{is_admin_project: True}``. The additional field can be used when
writing policy rules that evaluate access control to APIs.

Alternatively, in v3.10 the Identity API service introduced the concept of
system role assignments and system-scoped tokens. APIs that affect the
deployment system require system-scoped tokens.

The Identity API considers expired tokens as invalid, which is determined by
the deployment's configuration.

These authentication errors can occur:

**Authentication errors**

+------------------------+----------------------------------------------------------------------+
| Response code          | Description                                                          |
+------------------------+----------------------------------------------------------------------+
| ``Bad Request (400)``  | The Identity service failed to parse the request as expected. One    |
|                        | of the following errors occurred:                                    |
|                        |                                                                      |
|                        | - A required attribute was missing.                                  |
|                        |                                                                      |
|                        | - An attribute that is not allowed was specified, such as an ID on a |
|                        |   POST request in a basic CRUD operation.                            |
|                        |                                                                      |
|                        | - An attribute of an unexpected data type was specified.             |
+------------------------+----------------------------------------------------------------------+
| ``Unauthorized (401)`` | One of the following errors occurred:                                |
|                        |                                                                      |
|                        | - Authentication was not performed.                                  |
|                        |                                                                      |
|                        | - The specified ``X-Auth-Token`` header is not valid.                |
|                        |                                                                      |
|                        | - The authentication credentials are not valid.                      |
+------------------------+----------------------------------------------------------------------+
| ``Forbidden (403)``    | The identity was successfully authenticated but it is not            |
|                        | authorized to perform the requested action.                          |
+------------------------+----------------------------------------------------------------------+
| ``Not Found (404)``    | An operation failed because a referenced entity cannot be found by   |
|                        | ID. For a POST request, the referenced entity might be specified in  |
|                        | the request body rather than in the resource path.                   |
+------------------------+----------------------------------------------------------------------+
| ``Conflict (409)``     | A POST or PATCH operation failed. For example, a client tried to     |
|                        | update a unique attribute for an entity, which conflicts with that   |
|                        | of another entity in the same collection.                            |
|                        |                                                                      |
|                        | Or, a client issued a create operation twice on a collection with a  |
|                        | user-defined, unique attribute. For example, a client made a POST    |
|                        | ``/users`` request two times for the unique, user-defined name       |
|                        | attribute for a user entity.                                         |
+------------------------+----------------------------------------------------------------------+


Create explicit unscoped token with password and username
=========================================================

.. rest_method::  POST /v3/auth/tokens

Explicitly authenticate for an unscoped token using a password and a username.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - name: user_name_request_body_required
   - domain: user_domain_request_body_required
   - scope: explicit_unscoped_string_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/explicit-unscoped-password-username-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - methods: password_authentication_method_response_body_required
   - expires_at: expires_at_response_body_required
   - token: token_response_body_required
   - user: user_response_body_required
   - audit_ids: audit_ids_response_body_required
   - issued_at: issued_at_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-password-unscoped-response.json
   :language: javascript

Create explicit unscoped token with password and user ID
========================================================

.. rest_method::  POST /v3/auth/tokens

Explicitly authenticate for an unscoped token using a password and a user ID.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - id: user_id_request_body_required
   - scope: explicit_unscoped_string_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/explicit-unscoped-password-user-id-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - methods: password_authentication_method_response_body_required
   - expires_at: expires_at_response_body_required
   - token: token_response_body_required
   - user: user_response_body_required
   - audit_ids: audit_ids_response_body_required
   - issued_at: issued_at_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-password-unscoped-response.json
   :language: javascript

Create unscoped token with password and username
================================================

.. rest_method::  POST /v3/auth/tokens

Authenticate without specifying an authorization scope with a password and
username.

If the authenticating user has a ``default_project_id`` set on their user
reference and if they have a role assignment on that project, a project-scoped
token will be returned. If the user does not have a ``default_project_id``, or
does not have authorization on the project ID specified by the
``default_project_id`` attribute, an unscoped token will be returned.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - name: user_name_request_body_required
   - domain: user_domain_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/unscoped-password-username-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-password-unscoped-response.json
   :language: javascript


Create unscoped token with password and user ID
===============================================

.. rest_method::  POST /v3/auth/tokens

Authenticate without specifying an authorization scope with a password and user
ID.

If the authenticating user has a ``default_project_id`` set on their user
reference and if they have a role assignment on that project, a project-scoped
token will be returned. If the user does not have a ``default_project_id``, or
does not have authorization on the project ID specified by the
``default_project_id`` attribute, an unscoped token will be returned.

Request
-------

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - id: user_id_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/unscoped-password-user-id-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-password-unscoped-response.json
   :language: javascript

Create system-scoped token with password and username
=====================================================

.. rest_method::  POST /v3/auth/tokens

Authenticate for a token scoped to the deployment system using a password and
username.

The authentication request body must contain a ``system`` object within
``scope`` and the authenticating user must have a role assignment on the
deployment system.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - name: user_name_request_body_required
   - domain: user_domain_request_body_required
   - scope: system_scope_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/system-scoped-password-username-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - catalog: catalog_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - roles: roles_response_body_required
   - system: system_scope_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/auth/system-scoped-password-token-response.json
   :language: javascript

Create system-scoped token with password and user ID
====================================================

.. rest_method::  POST /v3/auth/tokens

Authenticate for a token scoped to the deployment system using a password and
user ID.

The authentication request body must contain a ``system`` object within
``scope`` and the authenticating user must have a role assignment on the
deployment system.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - id: user_id_request_body_required
   - scope: system_scope_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/system-scoped-password-user-id-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - catalog: catalog_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - roles: roles_response_body_required
   - system: system_scope_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/auth/system-scoped-password-token-response.json
   :language: javascript

Create domain-scoped token with password and username
=====================================================

.. rest_method::  POST /v3/auth/tokens

Authenticate for a token scoped to a domain using a password and username.

The authentication request body must contain a ``domain`` object within
``scope`` and the authenticating user must have a role assignment on the domain
in the request.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - name: user_name_request_body_required
   - domain: user_domain_request_body_required
   - scope: domain_scope_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/domain-scoped-password-username-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - catalog: catalog_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - roles: roles_response_body_required
   - domain: domain_scope_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/auth/domain-scoped-password-token-response.json
   :language: javascript

Create domain-scoped token with password and user ID
====================================================

.. rest_method::  POST /v3/auth/tokens

Authenticate for a token scoped to a domain using a password and a user ID.

The authentication request body must contain a ``domain`` object within
``scope`` and the authenticating user must have a role assignment on the domain
in the request.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - id: user_id_request_body_required
   - scope: domain_scope_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/domain-scoped-password-username-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - catalog: catalog_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - roles: roles_response_body_required
   - domain: domain_scope_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/auth/domain-scoped-password-token-response.json
   :language: javascript

Create project-scope token with password and username
=====================================================

.. rest_method::  POST /v3/auth/tokens

Authenticate for a token scoped to a project using a password and username.

The authentication request body must contain a ``project`` object within
``scope`` and the authenticating user must have a role assignment on the
project in the request.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - name: user_name_request_body_required
   - domain: user_domain_request_body_required
   - scope: project_scope_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/project-scoped-password-username-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - catalog: catalog_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - roles: roles_response_body_required
   - project: project_scope_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/auth/project-scoped-password-token-response.json
   :language: javascript

Create project-scope token with password and user ID
====================================================

.. rest_method::  POST /v3/auth/tokens

Authenticate for a token scoped to a project using a password and user ID.

The authentication request body must contain a ``project`` object within
``scope`` and the authenticating user must have a role assignment on the
project in the request.

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_request_parameters.yaml

   - auth: auth_request_body_required
   - identity: identity_request_body_required
   - methods: password_methods_request_body_required
   - password: password_request_body_required
   - user: user_request_body_required
   - id: user_id_request_body_required
   - scope: project_scope_request_body_required
   - nocatalog: nocatalog_query_string_optional

Example
~~~~~~~

.. literalinclude:: ./samples/auth/project-scoped-password-user-id-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: auth_response_parameters.yaml

   - X-Subject-Token: x_subject_token_response_header_required
   - token: token_response_body_required
   - audit_ids: audit_ids_response_body_required
   - catalog: catalog_response_body_required
   - expires_at: expires_at_response_body_required
   - issued_at: issued_at_response_body_required
   - methods: password_authentication_method_response_body_required
   - roles: roles_response_body_required
   - project: project_scope_response_body_required
   - user: user_response_body_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401

Example
~~~~~~~

.. literalinclude:: ./samples/auth/project-scoped-password-token-response.json
   :language: javascript

Token authentication with unscoped authorization
================================================

.. rest_method::  POST /v3/auth/tokens

Authenticates an identity and generates a token. Uses the token authentication method. Authorization is unscoped.

In the request body, provide the token ID.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_tokens``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - nocatalog: nocatalog
   - identity: identity
   - token: auth_token
   - id: auth_token_id
   - auth: auth
   - methods: auth_methods_token

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-token-unscoped-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Subject-Token: X-Subject-Token

Status Codes
~~~~~~~~~~~~
.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 409
   - 413
   - 415
   - 503

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-token-unscoped-response.json
   :language: javascript


Token authentication with scoped authorization
==============================================

.. rest_method::  POST /v3/auth/tokens

Authenticates an identity and generates a token. Uses the token authentication method and scopes authorization to a project or domain.

In the request body, provide the token ID and the ``project`` or
``domain`` authorization scope.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_tokens``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - nocatalog: nocatalog
   - methods: auth_methods_token
   - auth: auth
   - token: auth_token
   - audit_ids: audit_ids
   - scope: scope_string
   - id: auth_token_id
   - identity: identity

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-token-scoped-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Subject-Token: X-Subject-Token

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 409
   - 413
   - 415
   - 503

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-token-scoped-response.json
   :language: javascript


Token authentication with explicit unscoped authorization
=========================================================

.. rest_method::  POST /v3/auth/tokens

Authenticates an identity and generates a token.
Uses the token authentication method with explicit unscoped authorization.

In the request body, provide the token ID and the
``unscoped`` authorization scope.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_tokens``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - nocatalog: nocatalog
   - methods: auth_methods_token
   - auth: auth
   - token: auth_token
   - audit_ids: audit_ids
   - scope: explicit_unscoped_string
   - id: auth_token_id
   - identity: identity

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-token-explicit-unscoped-request.json
   :language: javascript

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Subject-Token: X-Subject-Token

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 409
   - 413
   - 415
   - 503

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-token-unscoped-response.json
   :language: javascript


Validate and show information for token
=======================================

.. rest_method::  GET /v3/auth/tokens

Validates and shows information for a token, including its expiration date and authorization scope.

Pass your own token in the ``X-Auth-Token`` request header.

Pass the token that you want to validate in the ``X-Subject-Token``
request header.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_tokens``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Auth-Token: X-Auth-Token
   - X-Subject-Token: X-Subject-Token
   - nocatalog: nocatalog
   - allow_expired: allow_expired

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Subject-Token: X-Subject-Token
   - domain: domain
   - methods: auth_methods
   - links: domain_link_response_body
   - user: user
   - token: token
   - expires_at: expires_at
   - project: project
   - system: system
   - catalog: catalog
   - roles: roles
   - audit_ids: audit_ids
   - issued_at: issued_at
   - id: user_id
   - name: user_name

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 413
   - 503

Example
~~~~~~~

.. literalinclude:: ./samples/admin/auth-token-unscoped-response.json
   :language: javascript


Check token
===========

.. rest_method::  HEAD /v3/auth/tokens

Validates a token.

This call is similar to ``GET /auth/tokens`` but no response body
is provided even in the ``X-Subject-Token`` header.

The Identity API returns the same response as when the subject
token was issued by ``POST /auth/tokens`` even if an error occurs
because the token is not valid. An HTTP ``204`` response code
indicates that the ``X-Subject-Token`` is valid.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_tokens``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Auth-Token: X-Auth-Token
   - X-Subject-Token: X-Subject-Token
   - allow_expired: allow_expired

Response
--------

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 413
   - 503

Revoke token
============

.. rest_method::  DELETE /v3/auth/tokens

Revokes a token.

This call is similar to the HEAD ``/auth/tokens`` call except that
the ``X-Subject-Token`` token is immediately not valid, regardless
of the ``expires_at`` attribute value. An additional
``X-Auth-Token`` is not required.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_tokens``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Auth-Token: X-Auth-Token
   - X-Subject-Token: X-Subject-Token

Response
--------

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 409
   - 413
   - 415
   - 503

Get service catalog
===================

.. rest_method:: GET /v3/auth/catalog

New in version 3.3

This call returns a service catalog for the X-Auth-Token provided in the
request, even if the token does not contain a catalog itself (for example,
if it was generated using ?nocatalog).

The structure of the catalog object is identical to that contained in a token.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_catalog``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Auth-Token: X-Auth-Token

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - endpoints: endpoints
   - id: service_id
   - type: service_type
   - name: service_name

Status Codes
~~~~~~~~~~~~


.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 409
   - 413
   - 415
   - 503

Example
~~~~~~~

.. literalinclude:: ./samples/admin/get-service-catalog-response.json
   :language: javascript


Get available project scopes
============================

.. rest_method:: GET /v3/auth/projects

New in version 3.3

This call returns the list of projects that are available to be scoped
to based on the X-Auth-Token provided in the request.

The structure of the response is exactly the same as listing projects
for a user.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_projects``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Auth-Token: X-Auth-Token

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - domain_id: project_domain_id_response_body
   - enabled: project_enabled_response_body
   - id: project_id
   - links: links_project
   - name: project_name_response_body

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 409
   - 413
   - 415
   - 503

Example
~~~~~~~

.. literalinclude:: ./samples/admin/get-available-project-scopes-response.json
   :language: javascript


Get available domain scopes
===========================

.. rest_method:: GET /v3/auth/domains

New in version 3.3

This call returns the list of domains that are available to be scoped
to based on the X-Auth-Token provided in the request.

The structure is the same as listing domains.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_domains``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Auth-Token: X-Auth-Token

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - description: domain_description_response_body
   - enabled: domain_enabled_response_body
   - id: domain_id_response_body
   - links: domain_link_response_body
   - name: domain_name_response_body

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 405
   - 409
   - 413
   - 415
   - 503

Example
~~~~~~~

.. literalinclude:: ./samples/admin/get-available-domain-scopes-response.json
   :language: javascript

Get available system scopes
===========================

.. rest_method:: GET /v3/auth/system

New in version 3.10

This call returns the list of systems that are available to be scoped
to based on the X-Auth-Token provided in the request.

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/auth_system``

Request
-------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - X-Auth-Token: X-Auth-Token

Response
--------

Parameters
~~~~~~~~~~

.. rest_parameters:: parameters.yaml

   - links: domain_link_response_body
   - system: response_body_system_required

Status Codes
~~~~~~~~~~~~

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 400

Example
~~~~~~~

.. literalinclude:: ./samples/admin/get-available-system-scopes-response.json
   :language: javascript
