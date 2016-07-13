.. -*- rst -*-

================
OS-EP-FILTER API
================

This API enables creation of ad-hoc catalogs for each project-scoped token
request. To do so, this API uses either static project-endpoint associations
or dynamic custom endpoints groups to associate service endpoints with
projects.

API Resources
=============

New In Version 1.1
==================

Endpoint Group
==============

Represents a dynamic collection of service endpoints having the same
characteristics, such as service_id, interface, or region. Indeed, any
endpoint attribute could be used as part of a filter.

A classic use case is to filter endpoints based on region. For example, suppose
a user wants to filter service endpoints returned in the service catalog by
region, the following endpoint group may be used:

.. literalinclude:: samples/OS-EP-FILTER/create-endpoint-group-request.json
   :language: javascript

This implies an Endpoint Group with filtering criteria of:

``region_id = "1b501"``

API Resources
=============

Project-Endpoint Associations
-----------------------------

If a valid X-Auth-Token token in not present in the HTTP header and/or the user
does not have the right authorization an HTTP ``401 Unauthorized`` is returned.

Create Association
==================

.. rest_method:: PUT /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/project_endpoint``

Modifies the endpoint resource adding an association between the project and
the endpoint.

Normal response codes: 204
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id
   - endpoint_id: endpoint_id

Response
--------

Status: 204 No Context

Check Association
=================

.. rest_method:: HEAD /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/project_endpoint``

Verifies the existence of an association between a project and an endpoint.

Normal response codes: 204
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id
   - endpoint_id: endpoint_id

List Associations for Project
=============================

.. rest_method:: GET /OS-EP-FILTER/projects/{project_id}/endpoints

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/project_endpoints``

Returns all the endpoints that are currently associated with a specific project.

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id
   - endpoint_id: endpoint_id

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/list-endpoints-response.json
   :language: javascript

Delete Association
==================

.. rest_method:: DELETE /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/project_endpoint``

Eliminates a previously created association between a project and an endpoint.

Normal response codes: 204
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id
   - endpoint_id: endpoint_id

Response
--------

Status: 204 No Content

Get projects associated with endpoint
=====================================

.. rest_method:: GET /OS-EP-FILTER/endpoints/{endpoint_id}/projects

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_projects``

Returns a list of projects that are currently associated with the given endpoint.

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_id: endpoint_id

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/get-projects-response.json
   :language: javascript

Endpoint Groups
===============

*New in version 1.1*

Required attributes:

``name (string)``

User-facing name of the service:

``filters (object)``

Describes the filtering performed by the endpoint group. The filter used must
be an ``endpoint`` property, such as ``interface``, ``service_id``,
``region_id`` and ``enabled``. Note that if using ``interface`` as a filter,
the only available values are ``public``, ``internal`` and ``admin``.

Optional attributes:

``description: (string)``

User-facing description of the service.

Create Endpoint Group Filter
============================

.. rest_method:: POST /OS-EP-FILTER/endpoint_groups

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_groups``

Normal response codes: 201
Error response codes: 401

Request
-------

.. literalinclude:: samples/OS-EP-FILTER/create-endpoint-group-request.json
   :language: javascript

Response
--------

Status: 201 Created

.. literalinclude:: samples/OS-EP-FILTER/endpoint-group-response.json
   :language: javascript

Get Endpoint Group
==================

.. rest_method:: GET /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group``

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters: parameters.yaml

   - endpoint_group_id: endpoint_group_id

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/endpoint-group-response.json
   :language: javascript

Check Endpoint Group
====================

.. rest_method:: HEAD /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group``

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id

Response
--------

Status: 200 OK

Update Endpoint Group
=====================

.. rest_method:: PATCH /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group``

The request block is the same as the one for create endpoint group, except that
only the attributes that are being updated need to be included.

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id

Request Example
---------------

.. literalinclude:: samples/OS-EP-FILTER/create-endpoint-group-request.json
   :language: javascript

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/endpoint-group-response.json
   :language: javascript

Remove Endpoint Group
=====================

.. rest_method::  DELETE /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group``

Normal response codes: 204
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id

Response
--------

Status: 204 No Content

List All Endpoint Groups
========================

.. rest_method:: GET /OS-EP-FILTER/endpoint_groups

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_groups``

Normal response codes: 200
Error response codes: 401

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/endpoint-groups-response.json
   :language: javascript

List Endpoint Groups Associated with Project
============================================

.. rest_method:: GET /OS-EP-FILTER/projects/{project_id}/endpoint_groups

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/project_endpoint_groups``

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/endpoint-groups-response.json
   :language: javascript

Create Endpoint Group to Project Association
============================================

.. rest_method:: PUT /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}/projects/{project_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group_project``

Normal response codes: 204
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id
   - project_id: project_id

Response
--------

Status: 204 No Content

Get Endpoint Group to Project Association
=========================================

.. rest_method:: GET /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}/projects/{project_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group_project``

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id
   - project_id: project_id

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/endpoint-project-response.json
   :language: javascript

Check Endpoint Group to Project Association
===========================================

.. rest_method:: HEAD /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}/projects/{project_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group_project``

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id
   - project_id: project_id

Response
--------

Status: 200 OK

Delete Endpoint Group to Project Association
============================================^

.. rest_method:: DELETE /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}/projects/{project_id}

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group_project``

Normal response codes: 204
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id
   - project_id: project_id

Response
--------

Status: 204 No Content

List Projects Associated with Endpoint Group
============================================

.. rest_method:: GET /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}/projects

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group_projects``

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/get-projects-response.json
   :language: javascript

List Service Endpoints Associated with Endpoint Group
=====================================================

.. rest_method:: GET /OS-EP-FILTER/endpoint_groups/{endpoint_group_id}/endpoints

Relationship:
``http://docs.openstack.org/api/openstack-identity/3/ext/OS-EP-FILTER/1.0/rel/endpoint_group_endpoints``

Normal response codes: 200
Error response codes: 401

Request
-------

.. rest_parameters:: parameters.yaml

   - endpoint_group_id: endpoint_group_id

Response
--------

Status: 200 OK

.. literalinclude:: samples/OS-EP-FILTER/list-service-endpoints.json
   :language: javascript
