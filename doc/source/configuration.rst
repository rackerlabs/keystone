..
      Copyright 2011-2012 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

====================
Configuring Keystone
====================

Setting up other OpenStack Services
===================================

Creating Service Users
----------------------

To configure the OpenStack services with service users, we need to create
a project for all the services, and then users for each of the services. We
then assign those service users an ``admin`` role on the service project. This
allows them to validate tokens - and to authenticate and authorize other user
requests.

Create a project for the services, typically named ``service`` (however, the
name can be whatever you choose):

.. code-block:: bash

    $ openstack project create service

Create service users for ``nova``, ``glance``, ``swift``, and ``neutron``
(or whatever subset is relevant to your deployment):

.. code-block:: bash

    $ openstack user create nova --password Sekr3tPass --project service

Repeat this for each service you want to enable.

Create an administrative role for the service accounts, typically named
``admin`` (however the name can be whatever you choose). For adding the
administrative role to the service accounts, you'll need to know the
name of the role you want to add. If you don't have it handy, you can look it
up quickly with:

.. code-block:: bash

    $ openstack role list

Once you have it, grant the administrative role to the service users.

.. code-block:: bash

    $ openstack role add admin --project service --user nova

Defining Services
-----------------

Keystone also acts as a service catalog to let other OpenStack systems know
where relevant API endpoints exist for OpenStack Services. The OpenStack
Dashboard, in particular, uses this heavily - and this **must** be configured
for the OpenStack Dashboard to properly function.

The endpoints for these services are defined in a template, an example of
which is in the project as the file ``etc/default_catalog.templates``.

Keystone supports two means of defining the services, one is the catalog
template, as described above - in which case everything is detailed in that
template.

The other is a SQL backend for the catalog service, in which case after
Keystone is online, you need to add the services to the catalog:

.. code-block:: bash

    $ openstack service create compute --name nova \
                                    --description "Nova Compute Service"
    $ openstack service create ec2 --name ec2 \
                                   --description "EC2 Compatibility Layer"
    $ openstack service create image --name glance \
                                      --description "Glance Image Service"
    $ openstack service create identity --name keystone \
                                        --description "Keystone Identity Service"
    $ openstack service create object-store --name swift \
                                     --description "Swift Service"


Identity sources
================

One of the most impactful decisions you'll have to make when configuring
keystone is deciding how you want keystone to source your identity data.
Keystone supports several different choices that will substantially impact how
you'll configure, deploy, and interact with keystone.

You can also mix-and-match various sources of identity (see `Domain-specific
Drivers`_ below for an example). For example, you can store OpenStack service
users and their passwords in SQL, manage customers in LDAP, and authenticate
employees via SAML federation.

.. support_matrix:: identity-support-matrix.ini

Public ID Generators
--------------------

Keystone supports a customizable public ID generator and it is specified in the
``[identity_mapping]`` section of the configuration file. Keystone provides a
sha256 generator as default, which produces regenerable public IDs. The
generator algorithm for public IDs is a balance between key size (i.e. the
length of the public ID), the probability of collision and, in some
circumstances, the security of the public ID. The maximum length of public ID
supported by keystone is 64 characters, and the default generator (sha256) uses
this full capability. Since the public ID is what is exposed externally by
keystone and potentially stored in external systems, some installations may
wish to make use of other generator algorithms that have a different trade-off
of attributes. A different generator can be installed by configuring the
following property:

* ``generator`` - identity mapping generator. Defaults to ``sha256``
  (implemented by :class:`keystone.identity.id_generators.sha256.Generator`)

.. WARNING::

    Changing the generator may cause all existing public IDs to be become
    invalid, so typically the generator selection should be considered
    immutable for a given installation.

Service Catalog
===============

Keystone provides two configuration options for managing a service catalog.

SQL-based Service Catalog (``sql.Catalog``)
-------------------------------------------

A dynamic database-backed driver fully supporting persistent configuration.

``keystone.conf`` example:

.. code-block:: ini

    [catalog]
    driver = sql

.. NOTE::

    A `template_file` does not need to be defined for the sql based catalog.

To build your service catalog using this driver, see the built-in help:

.. code-block:: bash

    $ openstack --help
    $ openstack service create --help
    $ openstack endpoint create --help

File-based Service Catalog (``templated.Catalog``)
--------------------------------------------------

The templated catalog is an in-memory backend initialized from a read-only
``template_file``. Choose this option only if you know that your service
catalog will not change very much over time.

.. NOTE::

    Attempting to change your service catalog against this driver will result
    in ``HTTP 501 Not Implemented`` errors. This is the expected behavior. If
    you want to use these commands, you must instead use the SQL-based Service
    Catalog driver.

``keystone.conf`` example:

.. code-block:: ini

    [catalog]
    driver = templated
    template_file = /opt/stack/keystone/etc/default_catalog.templates

The value of ``template_file`` is expected to be an absolute path to your
service catalog configuration. An example ``template_file`` is included in
keystone, however you should create your own to reflect your deployment.

Endpoint Filtering
==================

Endpoint Filtering enables creation of ad-hoc catalogs for each project-scoped
token request.

Configure the endpoint filter catalog driver in the ``[catalog]`` section.
For example:

.. code-block:: ini

    [catalog]
    driver = catalog_sql

In the ``[endpoint_filter]`` section, set ``return_all_endpoints_if_no_filter``
to ``False`` to return an empty catalog if no associations are made.
For example:

.. code-block:: ini

    [endpoint_filter]
    return_all_endpoints_if_no_filter = False

See `API Specification for Endpoint Filtering <https://developer.openstack.org/
api-ref/identity/v3-ext/#os-ep-filter-api>`_ for the details of API definition.

Endpoint Policy
===============

The Endpoint Policy feature provides associations between service endpoints
and policies that are already stored in the Identity server and referenced
by a policy ID.

Configure the endpoint policy backend driver in the ``[endpoint_policy]``
section. For example:

.. code-block:: ini

    [endpoint_policy]
    driver = sql

See `API Specification for Endpoint Policy <https://developer.openstack.org/
api-ref/identity/v3-ext/index.html#os-endpoint-policy-api>`_
for the details of API definition.

SSL
===

A secure deployment should have keystone running in a web server (such as
Apache httpd), or behind an SSL terminator.


OAuth1 1.0a
===========

The OAuth 1.0a feature provides the ability for Identity users to delegate
roles to third party consumers via the OAuth 1.0a specification.

To enable OAuth1:

1. Add the oauth1 driver to the ``[oauth1]`` section in ``keystone.conf``. For
   example:

.. code-block:: ini

    [oauth1]
    driver = sql

2. Add the ``oauth1`` authentication method to the ``[auth]`` section in
   ``keystone.conf``:

.. code-block:: ini

    [auth]
    methods = external,password,token,oauth1

3. If deploying under Apache httpd with ``mod_wsgi``, set the
   `WSGIPassAuthorization` to allow the OAuth Authorization headers to pass
   through `mod_wsgi`. For example, add the following to the keystone virtual
   host file:

.. code-block:: ini

    WSGIPassAuthorization On

See `API Specification for OAuth 1.0a <https://developer.openstack.org/
api-ref/identity/v3-ext/index.html#os-oauth1-api>`_ for the details of
API definition.


Token Binding
=============

Token binding refers to the practice of embedding information from external
authentication providers (like a company's Kerberos server) inside the token
such that a client may enforce that the token only be used in conjunction with
that specified authentication. This is an additional security mechanism as it
means that if a token is stolen it will not be usable without also providing
the external authentication.

To activate token binding you must specify the types of authentication that
token binding should be used for in ``keystone.conf`` e.g.:

.. code-block:: ini

    [token]
    bind = kerberos

Currently only ``kerberos`` is supported.

To enforce checking of token binding the ``enforce_token_bind`` parameter
should be set to one of the following modes:

* ``disabled`` disable token bind checking
* ``permissive`` enable bind checking, if a token is bound to a mechanism that
  is unknown to the server then ignore it. This is the default.
* ``strict`` enable bind checking, if a token is bound to a mechanism that is
  unknown to the server then this token should be rejected.
* ``required`` enable bind checking and require that at least 1 bind mechanism
  is used for tokens.
* named enable bind checking and require that the specified authentication
  mechanism is used. e.g.:

.. code-block:: ini

    [token]
    enforce_token_bind = kerberos

*Do not* set ``enforce_token_bind = named`` as there is not an authentication
mechanism called ``named``.

Limiting list return size
=========================

Keystone provides a method of setting a limit to the number of entities
returned in a collection, which is useful to prevent overly long response times
for list queries that have not specified a sufficiently narrow filter. This
limit can be set globally by setting ``list_limit`` in the default section of
``keystone.conf``, with no limit set by default. Individual driver sections may
override this global value with a specific limit, for example:

.. code-block:: ini

    [resource]
    list_limit = 100

If a response to ``list_{entity}`` call has been truncated, then the response
status code will still be 200 (OK), but the ``truncated`` attribute in the
collection will be set to ``true``.


Health Check middleware
=======================

This health check middleware allows an operator to configure the endpoint URL
that will provide information to a load balancer if the given API endpoint at
the node should be available or not.

To enable the health check middleware, it must occur in the beginning of the
application pipeline.

The health check middleware should be placed in your
``keystone-paste.ini`` in a section titled ``[filter:healthcheck]``.
It should look like this::

  [filter:healthcheck]
  use = egg:oslo.middleware#healthcheck

Desired keystone application pipelines have been defined with this filter,
looking like so::

  [pipeline:public_version_api]
  pipeline = healthcheck cors sizelimit osprofiler url_normalize public_version_service

It's important that the healthcheck go to the front of the pipeline for the
most efficient checks.

For more information and configuration options for the middleware see
`oslo.middleware <https://docs.openstack.org/oslo.middleware/latest/reference/healthcheck_plugins.html>`_.

.. _`API protection with RBAC`:

API protection with Role Based Access Control (RBAC)
=====================================================

Like most OpenStack projects, keystone supports the protection of its APIs by
defining policy rules based on an RBAC approach. These are stored in a JSON
policy file, the name and location of which is set in the main keystone
configuration file.

Each keystone v3 API has a line in the policy file which dictates what level of
protection is applied to it, where each line is of the form::

  <api name>: <rule statement> or <match statement>

where:

``<rule statement>`` can contain ``<rule statement>`` or ``<match statement>``

``<match statement>`` is a set of identifiers that must match between the token
provided by the caller of the API and the parameters or target entities of the
API call in question. For example:

.. code-block:: javascript

    "identity:create_user": "role:admin and domain_id:%(user.domain_id)s"

Indicates that to create a user you must have the admin role in your token and
in addition the domain_id in your token (which implies this must be a domain
scoped token) must match the domain_id in the user object you are trying to
create. In other words, you must have the admin role on the domain in which you
are creating the user, and the token you are using must be scoped to that
domain.

Each component of a match statement is of the form::

  <attribute from token>:<constant> or <attribute related to API call>

The following attributes are available

* Attributes from token: user_id, the domain_id or project_id depending on
  the scope, and the list of roles you have within that scope

* Attributes related to API call: Any parameters that are passed into the API
  call are available, along with any filters specified in the query string.
  Attributes of objects passed can be referenced using an object.attribute
  syntax (e.g. user.domain_id). The target objects of an API are also available
  using a target.object.attribute syntax. For instance:

  .. code-block:: javascript

    "identity:delete_user": "role:admin and domain_id:%(target.user.domain_id)s"

  would ensure that the user object that is being deleted is in the same
  domain as the token provided.

Every target object (except token) has an `id` and a `name` available as
`target.<object>.id` and `target.<object>.name`. Other attributes are retrieved
from the database and vary between object types. Moreover, some database fields
are filtered out (e.g. user passwords).

List of object attributes:

* role:
    * target.role.domain_id
    * target.role.id
    * target.role.name

* user:
    * target.user.default_project_id
    * target.user.description
    * target.user.domain_id
    * target.user.enabled
    * target.user.id
    * target.user.name
    * target.user.password_expires_at

* group:
    * target.group.description
    * target.group.domain_id
    * target.group.id
    * target.group.name

* domain:
    * target.domain.description
    * target.domain.enabled
    * target.domain.id
    * target.domain.name

* project:
    * target.project.description
    * target.project.domain_id
    * target.project.enabled
    * target.project.id
    * target.project.is_domain
    * target.project.name
    * target.project.parent_id

* token
    * target.token.user_id
    * target.token.user.domain.id

The default policy.json file supplied provides a somewhat basic example of API
protection, and does not assume any particular use of domains. For multi-domain
configuration installations where, for example, a cloud provider wishes to
allow administration of the contents of a domain to be delegated, it is
recommended that the supplied policy.v3cloudsample.json is used as a basis for
creating a suitable production policy file. This example policy file also shows
the use of an admin_domain to allow a cloud provider to enable cloud
administrators to have wider access across the APIs.

A clean installation would need to perhaps start with the standard policy file,
to allow creation of the admin_domain with the first users within it. The
domain_id of the admin domain would then be obtained and could be pasted into a
modified version of policy.v3cloudsample.json which could then be enabled as
the main policy file.

.. _`prepare your deployment`:

Preparing your deployment
=========================

Step 1: Configure keystone.conf
-------------------------------

Ensure that your ``keystone.conf`` is configured to use a SQL driver:

.. code-block:: ini

    [identity]
    driver = sql

You may also want to configure your ``[database]`` settings to better reflect
your environment:

.. code-block:: ini

    [database]
    connection = sqlite:///keystone.db
    idle_timeout = 200

.. NOTE::

    It is important that the database that you specify be different from the
    one containing your existing install.

Step 2: Sync your new, empty database
-------------------------------------

You should now be ready to initialize your new database without error, using:

.. code-block:: bash

    $ keystone-manage db_sync

To test this, you should now be able to start keystone:

.. code-block:: bash

    $ uwsgi --http 127.0.0.1:35357 --wsgi-file $(which keystone-wsgi-admin)

And use the OpenStack Client to list your projects (which should successfully
return an empty list from your new database):

.. code-block:: bash

    $ openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v3/ project list

.. NOTE::

    We're providing the default OS_TOKEN and OS_URL values from
    ``keystone.conf`` to connect to the keystone service. If you changed those
    values, or deployed keystone to a different endpoint, you will need to
    change the provided command accordingly.

Supported clients
=================

There are two supported clients, `python-keystoneclient`_ project provides
python bindings and `python-openstackclient`_ provides a command line
interface.

.. _`python-openstackclient`: https://docs.openstack.org/python-openstackclient/latest
.. _`python-keystoneclient`: https://docs.openstack.org/python-keystoneclient/latest


Authenticating with a Password via CLI
--------------------------------------

To authenticate with keystone using a password and ``python-openstackclient``,
set the following flags, note that the following user referenced below should
be granted the ``admin`` role.

* ``--os-username OS_USERNAME``: Name of your user
* ``--os-password OS_PASSWORD``: Password for your user
* ``--os-project-name OS_PROJECT_NAME``: Name of your project
* ``--os-auth-url OS_AUTH_URL``: URL of the keystone authentication server

You can also set these variables in your environment so that they do not need
to be passed as arguments each time:

.. code-block:: bash

    $ export OS_USERNAME=my_username
    $ export OS_PASSWORD=my_password
    $ export OS_PROJECT_NAME=my_project
    $ export OS_AUTH_URL=http://localhost:35357/v3

For example, the commands ``user list``, ``token issue`` and ``project create``
can be invoked as follows:

.. code-block:: bash

    # Using password authentication, with environment variables
    $ export OS_USERNAME=admin
    $ export OS_PASSWORD=secret
    $ export OS_PROJECT_NAME=admin
    $ export OS_AUTH_URL=http://localhost:35357/v3
    $ openstack user list
    $ openstack project create demo
    $ openstack token issue

    # Using password authentication, with flags
    $ openstack --os-username=admin --os-password=secret --os-project-name=admin --os-auth-url=http://localhost:35357/v3 user list
    $ openstack --os-username=admin --os-password=secret --os-project-name=admin --os-auth-url=http://localhost:35357/v3 project create demo
