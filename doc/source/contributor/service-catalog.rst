..
    Licensed under the Apache License, Version 2.0 (the "License"); you may not
    use this file except in compliance with the License. You may obtain a copy
    of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.

========================
Service Catalog Overview
========================

The OpenStack keystone service catalog allows API clients to dynamically
discover and navigate to cloud services. The service catalog may differ from
deployment-to-deployment, user-to-user, and tenant-to-tenant.

The service catalog is the first hurdle that API consumers will need to
understand after successfully authenticating with Keystone, making it a
critical focal point for the overall user experience of OpenStack.

*If you're integrating your OpenStack service with Keystone*, then please
follow the guidelines provided below.

*If you're writing an OpenStack client*, hopefully this helps you navigate the
service catalog that you're being presented so that you can quickly move on to
the business of consuming cloud services.

An example service catalog
==========================

The following is an example service catalog. It actually excludes several
common attributes such as ids, which are of no concern to end users,
region_ids, which are a bit out of scope for this topic, and enabled, which is
literally always true for end users.

This service catalog contains just one service, "Keystone", which is accessible
via a single endpoint URL:

.. code-block:: json

   {
       "catalog": [
           {
               "name": "Keystone",
               "type": "identity",
               "endpoints": [
                   {
                       "interface": "public",
                       "url": "https://identity.example.com:35357/"
                   }
               ]
           }
       ]
    }

The service catalog itself may appear in a token creation response (``POST
/v3/auth/tokens``), a token validation response (``GET /v3/auth/tokens``), or
as a standalone resource (``GET /v3/auth/catalog``).

Services
========

The service catalog itself is composed of a list of services.

Service entities represent web services in the OpenStack deployment. A service
may have zero or more endpoints associated with it, although a service with
zero endpoints is essentially useless in an OpenStack configuration.

In addition to the related endpoints, there are two attributes of services that
important to end users:

Names
-----

* ``name`` (string): user-facing name of the service

This attribute is not intended to be machine-parseable or otherwise meaningful
beyond branding or name-recognition for end users. Logical values might include
"Keystone" or maybe "Brand X Public Cloud Identity Service". Deployers should
be free to rename, and therefore rebrand, a service at will.

Types
-----

* ``type`` (string): describes the API implemented by the service. The
  following values are recognized within the OpenStack ecosystem: ``compute``,
  ``image``, ``ec2``, ``identity``, ``volume``, ``network``. To support
  non-core and future projects, the value should not be validated against this
  list.

This should not convey the version of the API implemented by the service (as in
Cinder's ``volumev2`` service type) because both the ``volume`` service and
``volumev2`` service provide "block storage as a service" which is what the
service type is meant to convey. The underlying implementation is completely
irrelevant here.

In the general case, there should only be one service in a deployment per
service type, although Keystone does not enforce this today.

Endpoints
=========

Each service should have one or more related endpoints. An endpoint is
essentially a base URL for an API, along with some metadata about the endpoint
itself and represent URL endpoints for OpenStack web services.

Interfaces
----------

* ``interface`` (string): describes the visibility of the endpoint according to
  one of three values (``public``, ``internal``, and ``admin``)

**Public** endpoints are intended for consumption by end users, generally on a
publicly available network interface.

**Internal** endpoints are intended for consumption by end users, generally on
an unmetered internal network interface.

**Admin** endpoints are intended only for consumption by those needing
administrative access to the service, generally on a secure network interface.

Most services should not provide anything other than a public URL. You might
also think of each interface value as the result of a matrix of use cases:

* Public API on a public network: use a public interface.
* Public API on an internal network: use an internal interface.
* Privileged API on a public network: unsupported! Use access controls on your
  public endpoint instead.
* Privileged API on an internal network: admin interface, but use access
  controls on your public endpoint instead. The notion of a "privileged API"
  endpoint makes security-conscious developers instantly lazy (security becomes
  someone else's problem), and is an obvious attack vector if someone were to
  infiltrate your internal network. It also adds more complexity to your API
  architecture which makes documentation, testing, and API evolution that much
  more difficult.

URLs
----

* ``url`` (string): fully qualified URL of the service endpoint

This should be unversioned base URL for an API. Good examples include
``https://identity.example.com:35357/`` and ``https://keystone.example.com/``.

Conversely, ``https://identity.example.com:35357/v2.0/`` is an unfortunate
example because it directs all clients to connect to a versioned endpoint,
regardless of which API versions they understand. This makes it hard for
services to do any sort of API versioning, and for clients to dynamically
discover additional available versions.

For a period of time, keystone was stuck in a position where it implements a
``/v3/`` API, but for backwards compatibility with existing v2 clients, was
forced to continue advertising the ``/v2.0/`` endpoint in the service catalog
until it was reasonale to assume that all clients in the ecosystem are capable
of handling an unversioned URL. As a side effect, this has had a tremendous
impact on the awareness of, and thus adoption of, Keystone's Identity API v3
(which has been enabled by default — and stable — since the 2013.1 Grizzly
release). Don't put your project in that position!

Similarly, ``https://object-store.example.com/v1/KEY_\$(tenant_id)s`` (which
would ultimately be rendered to clients as a tenant-specific URL, such as
``https://object-store.example.com/v1/KEY_d12af07f4e2c4390a21acc31517ebec9``)
is an unfortunate example because not only does it hardcode an API version as
in the above example, but it also exposes the client's tenancy directly to the
client — which happens to be completely redundant with the authorization
context provided to services by keystonemiddleware.auth_token using the
client's authentication token. It's also far less cacheable than a URL that is
neither tenant nor user specific, which is important given that every client
needs access to consume the service catalog prior to nearly every API request.
