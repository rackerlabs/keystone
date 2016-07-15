.. -*- rst -*-

========
Services
========


Shows service information by ID
===============================

.. rest_method::  GET /v2.0/services/{serviceId}

Shows information for a service, by ID.

Normal response codes: 200, 203
Error response codes: 413, 405, 404, 403, 401, 400, 503

Request
-------

.. rest_parameters:: parameters.yaml

   - serviceId: serviceId

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - type: type
   - description: description
   - name: name
   - id: id

Response Example
----------------

.. literalinclude:: samples/admin/service-show-response.json
   :language: javascript


Delete service
==============

.. rest_method::  DELETE /v2.0/services/{serviceId}

Deletes a service.

Normal response codes: 204
Error response codes: 413, 415, 405, 404, 403, 401, 400, 503, 409

Request
-------

.. rest_parameters:: parameters.yaml

   - serviceId: serviceId


List services
=============

.. rest_method::  GET /v2.0/services

Lists all services.

Normal response codes: 200, 203
Error response codes: 413,405, 404, 403, 401, 400, 503

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - type: type
   - description: description
   - name: name
   - id: id

Response Example
----------------

.. literalinclude:: samples/admin/services-list-response.json
   :language: javascript


Create service
==============

.. rest_method::  POST /v2.0/services

Creates a service.

Normal response codes: 201
Error response codes: 413, 415, 405, 404, 403, 401, 400, 503, 409

Request Example
---------------

.. literalinclude:: samples/admin/service-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - Location: Location
   - type: type
   - description: description
   - name: name
   - id: id


Show service information by name
================================

.. rest_method::  GET /v2.0/services/{serviceName}

Shows information for a service, by name.

Normal response codes: 200, 203
Error response codes: 413, 405, 404, 403, 401, 400, 503

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - type: type
   - description: description
   - name: name
   - id: id

Response Example
----------------

.. literalinclude:: samples/admin/service-show-response.json
   :language: javascript
