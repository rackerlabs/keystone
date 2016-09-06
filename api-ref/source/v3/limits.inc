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

List limits
===========

.. rest_method:: GET /v3/limits

NOTE(bbobrov): not sure how to do it -- via /v3/limits?project.id={project_id} or /v3/limits/projects/{project_id}

For example, GET /v3/limits?project.id={project_id} or GET /v3/limits?region.id={region_id}&user.id={user_id}
