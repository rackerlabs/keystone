.. -*- rst -*-

==================
 Quota limits API
==================

Creates, reads, updates, deletes quota limits.


Create a global limit for service
=================================

.. rest_method:: PUT /v3/limits/regions/{region_id}/services/{service_id}

Normal response codes: 204

Request
-------

.. rest_parameters:: parameters.yaml

   - region_id: region_id_path
   - service_id: service_id_path
   - resource: resource_body
   - limit: limit_body


Create a user-associated limit
==============================

.. rest_method:: PUT /v3/limits/regions/{region_id}/services/{service_id}/users/{user_id}

Request
-------

.. rest_parameters:: parameters.yaml

   - region_id: region_id_path
   - service_id: service_id_path
   - user_id: user_id_path
   - resource: resource_body
   - limit: limit_body


Create a project-associated limit
=================================

.. rest_method:: PUT /v3/limits/regions/{region_id}/services/{service_id}/projects/{project_id}

Request
-------

.. rest_parameters:: parameters.yaml

   - region_id: region_id_path
   - service_id: service_id_path
   - project_id: project_id_path
   - resource: resource_body
   - limit: limit_body

List limits for a project
=========================

.. rest_method:: GET /v3/limits/regions/<region_id>/services/<service_type>/projects/<project_id>?include_parents

Get limit for a project on a service

Request
-------

.. rest_parameters:: parameters.yaml

   - region_id: region_id_path
   - service_type: service_type_path
   - project_id: project_id_path

Response Example
----------------

.. literalinclude:: ./samples/admin/project-limits.json
   :language: javascript

Get resource limit
==================

.. rest_method:: GET /v3/limits/regions/<region_id>/services/<service_type>/resource/<resource_id>

Get limit for a resource

.. rest_parameters:: parameters.yaml

   - region_id: region_id_path
   - service_type: service_type_path
   - resource: resource_id_path
