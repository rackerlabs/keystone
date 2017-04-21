.. -*- rst -*-

======
Routes
======

OpenStack services typically determine whether a user's API request should be
allowed using Role Based Access Control (RBAC). For OpenStack this means the
service compares the roles that user has on the project (as indicated by the
roles in the token), against the roles required for the API in question
(as defined in the service's policy file). A user obtains roles on a project by
having these assigned to them via the Identity service API.


List Routes
===========

.. rest_method::  GET /v3/routes

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/routes``

Lists routes.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

   - service: service_type_query
   - verb: verb_query
   - path: path_query
   - role_id: role_id_query

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - links: link_collection
   - routes: routes
   - domain_id: domain_id_response_body
   - id: role_id_response_body
   - links: link_response_body
   - name: role_name_response_body

Response Example
----------------

.. literalinclude:: ./samples/admin/roles-list-response.json
   :language: javascript


Create role
===========

.. rest_method::  POST /v3/routes

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/routes``

Creates a route.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 409

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

   - role: role
   - name: role_name_create_body
   - domain_id: domain_id_response_body

Request Example
---------------

.. literalinclude:: ./samples/admin/role-create-request.json
   :language: javascript

Request Example for Domain Specific Role
----------------------------------------

.. literalinclude:: ./samples/admin/domain-specific-role-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - role: role
   - domain_id: domain_id_response_body
   - id: role_id_response_body
   - links: link_response_body
   - name: role_name_response_body


Show role details
=================

.. rest_method::  GET /v3/roles/{role_id}

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/role``

Shows details for a role.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

   - role_id: role_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - role: role
   - domain_id: domain_id_response_body
   - id: role_id_response_body
   - links: link_response_body
   - name: role_name_response_body

Response Example
----------------

.. literalinclude:: ./samples/admin/role-show-response.json
   :language: javascript


Update role
===========

.. rest_method::  PATCH /v3/roles/{role_id}

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/role``

Updates a role.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

   - role_id: role_id_path
   - role: role
   - name: role_name_update_body

Request Example
---------------

.. literalinclude:: ./samples/admin/role-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - role: role
   - domain_id: domain_id_response_body
   - id: role_id_response_body
   - links: link_response_body
   - name: role_name_response_body

Response Example
----------------

.. literalinclude:: ./samples/admin/role-update-response.json
   :language: javascript


Delete role
===========

.. rest_method::  DELETE /v3/routes/{role_id}

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/role``

Deletes a role.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

   - role_id: role_id_path
