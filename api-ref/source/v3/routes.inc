.. -*- rst -*-

======
Routes
======

# FIXME(knikolla): Write documentation here.

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
   - id: route_id_response_body
   - path: path_response_body
   - role_id: role_id_response_body
   - links: link_response_body
   - service: service_type
   - verb: verb_response_body

Response Example
----------------

.. literalinclude:: ./samples/admin/routes-list-response.json
   :language: javascript


Create route
===========

.. rest_method::  POST /v3/routes

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/route``

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

   - route: route
   - path: path_response_body
   - role: role_id_response_body
   - service: service_type
   - verb: verb_response_body

Request Example
---------------

.. literalinclude:: ./samples/admin/route-create-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - route: route
   - service: service_type
   - links: link_response_body
   - role_id: role_id_response_body
   - verb: verb_response_body
   - path: path_response_body
   - id: route_id_response_body

Response Example
----------------
.. literalinclude:: ./samples/admin/route-create-response.json
   :language: javascript


Show route details
=================

.. rest_method::  GET /v3/routes/{route_id}

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/route``

Shows details for a route.

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

   - route_id: route_id_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - route: route
   - service: service_type
   - links: link_response_body
   - role_id: role_id_response_body
   - verb: verb_response_body
   - path: path_response_body
   - id: route_id_response_body

Response Example
----------------

.. literalinclude:: ./samples/admin/route-show-response.json
   :language: javascript


Update role
===========

.. rest_method::  PATCH /v3/routes/{route_id}

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/route``

Updates a route.

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

   - route: route
   - path: path_response_body
   - role: role_id_response_body
   - service: service_type
   - verb: verb_response_body

Request Example
---------------

.. literalinclude:: ./samples/admin/route-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - route: route
   - service: service_type
   - links: link_response_body
   - role_id: role_id_response_body
   - verb: verb_response_body
   - path: path_response_body
   - id: route_id_response_body

Response Example
----------------

.. literalinclude:: ./samples/admin/route-update-response.json
   :language: javascript


Delete role
===========

.. rest_method::  DELETE /v3/routes/{route_id}

Relationship: ``https://docs.openstack.org/api/openstack-identity/3/rel/route``

Deletes a route.

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

   - route_id: route_id_path
