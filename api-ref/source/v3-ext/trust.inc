.. -*- rst -*-

==============
 OS-TRUST API 
==============

Creates a trust.

A trust is an OpenStack Identity extension that enables delegation
and, optionally, impersonation through ``keystone``. A trust
extension defines a relationship between a trustor and trustee. A
trustor is the user who delegates a limited set of their own rights
to another user, known as the trustee, for a limited time.

The trust can eventually enable the trustee to impersonate the
trustor. For security reasons, some safety measures are added. For
example, if a trustor loses a given role, the API automatically
revokes any trusts and the related tokens that the user issued with
that role.

For more information, see `Use trusts <http://docs.openstack.org
/admin-guide/keystone_use_trusts.html>`_.


Create trust
============

.. rest_method::  POST /v3/OS-TRUST/trusts

Creates a trust.

Response codes: 201, 400, 401, 403, 404, 405, 409, 413, 415, 503

Request
-------

.. rest_parameters:: parameters.yaml

   - impersonation: impersonation
   - trust: trust
   - trustor_user_id: trustor_user_id
   - name: name
   - roles: roles
   - expires_at: expires_at
   - remaining_uses: remaining_uses
   - trustee_user_id: trustee_user_id
   - project_id: project_id

Request Example
---------------

Status: 201 Created

.. literalinclude:: samples/OS-TRUST/trust-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - impersonation: impersonation
   - roles_links: roles_links
   - trust: trust
   - trustor_user_id: trustor_user_id
   - name: name
   - links: links
   - expires_at: expires_at
   - remaining_uses: remaining_uses
   - trustee_user_id: trustee_user_id
   - roles: roles
   - project_id: project_id

Response Example
----------------

.. literalinclude:: samples/OS-TRUST/trust-create-response.json
   :language: javascript

List trusts
===========

.. rest_method:: GET /v3/OS-TRUST/trusts

Lists all trusts.

Response codes: 200, 400, 401, 403, 404, 405, 413, 503

The following optional query strings are supported:

- ``page``
- ``per_page``
- ``trustor_user_id``
- ``trustee_user_id``

In order to list trusts for a given trustor, filter the collection using a query string (e.g., ``?trustor_user_id={user_id}``).

::

   GET /v3/OS-TRUST/trusts?trustor_user_id=a0fdfd

In order to list trusts for a given trustee, filter the collection using a query string (e.g., ``?trustee_user_id={user_id}``).

::

   GET /v3/OS-TRUST/trusts?trustee_user_id=86c0d5

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - trusts: trusts
   - id: id
   - expires_at: expires_at
   - impersonation: impersonation
   - links: links
   - roles: roles
   - roles_links: roles_links
   - name: name
   - project_id: project_id
   - trustee_user_id: trustee_user_id
   - trustor_user_id: trustor_user_id
   - remaining_uses: remaining_uses
   - redelegation_count: redelegation_count
   - redelegated_trust_id: redelegated_trust_id

Response Example
----------------

Status: 200 OK

.. literalinclude:: samples/OS-TRUST/trust-list-response.json
   :language: javascript


Get trust
=========

.. rest_method:: GET /v3/OS-TRUST/trusts/{trust_id}

Gets the trust information for ``{trust_id}``.

Response codes: 200, 400, 401, 403, 404, 405, 413, 503

Request
-------

.. rest_parameters:: parameters.yaml

   - trust_id: trust_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - trust: trust
   - id: id
   - expires_at: expires_at
   - impersonation: impersonation
   - links: links
   - roles: roles
   - roles_links: roles_links
   - name: name
   - project_id: project_id
   - trustee_user_id: trustee_user_id
   - trustor_user_id: trustor_user_id
   - remaining_uses: remaining_uses
   - redelegation_count: redelegation_count
   - redelegated_trust_id: redelegated_trust_id

Response Example
----------------

Status: 200 OK

.. literalinclude:: samples/OS-TRUST/trust-get-response.json
   :language: javascript


Delete trust
============

.. rest_method:: DELETE /v3/OS-TRUST/trusts/{trust_id}

Deletes a trust with ``{trust_id}``.

Response codes: 204, 400, 401, 403, 404, 405, 409, 413, 415, 503

Request
-------

.. rest_parameters:: parameters.yaml

   - trust_id: trust_id

Response Example
----------------

Status: 204 No Content


List roles delegated by a trust
===============================

.. rest_method:: GET /v3/OS-TRUST/trusts/{trust_id}/roles

Lists roles delegated by a trust with ``{trust_id}``.

Response codes: 200, 400, 401, 403, 404, 405, 413, 503

Request
-------

.. rest_parameters:: parameters.yaml

   - trust_id: trust_id

Response Example
----------------

.. literalinclude:: samples/OS-TRUST/trust-list-roles-delegated-response.json
   :language: javascript


Check if a role is delegated by a trust
=======================================

.. rest_method:: HEAD /v3/OS-TRUST/trusts/{trust_id}/roles/{role_id}

Checks if a role is delegated by a trust.

Response Codes: 200, 400, 401, 403, 404, 405, 413, 503

Request
-------

.. rest_parameters:: parameters.yaml

   - trust_id: trust_id
   - role_id: role_id

Response Example
----------------

Status: 200 OK


Get role delegated by a trust
=============================

.. rest_method:: GET /v3/OS-TRUST/trusts/{trust_id}/roles/{role_id}

Gets a role with delegated by a trust.

Response Codes: 200, 400, 401, 403, 404, 405, 413, 503

Request
-------

.. rest_parameters:: parameters.yaml

   - trust_id: trust_id
   - role_id: role_id

Response Example
----------------

Status: 200 OK

.. literalinclude:: samples/OS-TRUST/trust-get-role-delegated-response.json
   :language: javascript
