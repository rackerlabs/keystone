.. keystone documentation master file, created by
   sphinx-quickstart on Mon May 23 07:54:13 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

:tocdepth: 2

==============
 Keystone API
==============

.. rest_expand_all::

===============================
 Identity API v2.0 (DEPRECATED)
===============================

.. include:: v2/identity-api-extensions.inc
.. include:: v2/versions.inc
.. include:: v2/identity-auth.inc
.. include:: v2/overview.inc

=====================================
 Identity Admin API v2.0 (DEPRECATED)
=====================================

.. include:: v2-admin/admin-tenants.inc
.. include:: v2-admin/admin-tokens.inc
.. include:: v2-admin/admin-users.inc
.. include:: v2-admin/admin-endpoints.inc
.. include:: v2-admin/admin-versions.inc

==========================================
 Identity API v2.0 extensions (DEPRECATED)
==========================================

.. include:: v2-ext/ksadm-admin.inc
.. include:: v2-ext/ksec2-admin.inc
.. include:: v2-ext/kscrud.inc

===========================
 Identity API v3 (CURRENT)
===========================

The Identity service generates authentication tokens that permit access to the
OpenStack services REST APIs. Clients obtain this token and the URL endpoints
for other service APIs by supplying their valid credentials to the
authentication service.

Each time you make a REST API request to an OpenStack service, you supply your
authentication token in the X-Auth-Token request header.

Like most OpenStack projects, OpenStack Identity protects its APIs by defining
policy rules based on a role-based access control (RBAC) approach.

The Identity service configuration file sets the name and location of a JSON
policy file that stores these rules.

For information about Identity API protection, see
`Identity API protection with role-based access control (RBAC)
<http://docs.openstack.org/admin-guide/identity_service_api_protection.html>`_
in the OpenStack Cloud Administrator Guide.

This section lists the Identity API operations in the following order:

* `Authentication and token management`_
* `Credentials`_
* `Domains`_
* `Domain configuration`_
* `Groups`_
* `Policies`_
* `Projects`_
* `Regions`_
* `Roles`_
* `Service catalog and endpoints`_
* `Users`_
* `OS-INHERIT API`_

.. include:: v3/authenticate-v3.inc
.. include:: v3/credentials.inc
.. include:: v3/domains.inc
.. include:: v3/domains-config-v3.inc
.. include:: v3/groups.inc
.. include:: v3/inherit.inc
.. include:: v3/policies.inc
.. include:: v3/projects.inc
.. include:: v3/regions-v3.inc
.. include:: v3/roles.inc
.. include:: v3/service-catalog.inc
.. include:: v3/users.inc

======================================
 Identity API v3 extensions (CURRENT)
======================================

This section describes these Identity API v3 extensions:

* `OS-ENDPOINT-POLICY API`_
* `OS-OAUTH1 API`_
* `OS-TRUST API`_
* `OS-REVOKE API`_
* `OS-EP-FILTER API`_
* `OS-FEDERATION API`_

.. include:: v3-ext/endpoint-policy.inc
.. include:: v3-ext/oauth.inc
.. include:: v3-ext/trust.inc
.. include:: v3-ext/revoke.inc
.. include:: v3-ext/ep-filter.inc
.. include:: v3-ext/federation.inc
