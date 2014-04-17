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

===================================
Configuring Keystone for Federation
===================================

Definitions
-----------

* `Service Provider (SP)`: provides a service to an end-user.
* `Identity Provider (IdP)`: service that stores information about users and
  groups.
* `SAML assertion`: contains information about a user as provided by an IdP.

Prerequisites
-------------

This approach to federation supports Keystone as a Service Provider, consuming
SAML assertions issued by an external Identity Provider.

Federated users are not mirrored in the Keystone identity backend
(for example, using the SQL driver). The external Identity Provider is
responsible for authenticating users, and communicates the result of
authentication to Keystone using SAML assertions. Keystone then maps the SAML
assertions to Keystone user groups, and assignments created in Keystone.

To enable federation, you'll need to:

1. Run Keystone under Apache, rather than using ``keystone-all``.
2. Setup `Shibboleth <https://wiki.shibboleth.net/confluence/display/SHIB2/Home>`_
   (using ``mod_shib``, an Apache
   module), which handles the SAML2 handshake.
3. Enable ``OS-FEDERATION`` extension.

Run Keystone under Apache
~~~~~~~~~~~~~~~~~~~~~~~~~

Follow the steps outlined at: `Running Keystone in HTTPD`_.

.. _`Running Keystone in HTTPD`: apache-httpd.html

You'll also need to install `Shibboleth <https://wiki.shibboleth.net/confluence/display/SHIB2/Home>`_ , for
example::

    $ apt-get libapache2-mod-shib2

Enable the Keystone virtual host, for example::

    $ a2ensite wsgi-keystone.conf

Enable the ``ssl`` and ``shib2`` modules, for example::

    $ a2enmod ssl
    $ a2enmod shib2

Restart Apache, for example::

    $ service apache2 restart

Setup Shibboleth (``mod_shib``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Federate Keystone (SP) and an external IdP.

Once you have your Keystone virtual host ready, it's then time to
configure Shibboleth and upload your Metadata to the Identity Provider.

If new certificates are required, they can be easily created by executing::

    $ shib-keygen -y <number of years>

The newly created file will be stored under ``/etc/shibboleth/sp-key.pem``

You should fetch your Service Provider's Metadata file. Typically this can be
achieved by simply fetching a Metadata file, for example::

    $ wget --no-check-certificate -O <name of the file> https://service.example.org/Shibboleth.sso/Metadata

Upload your Service Provider's Metadata file to your Identity Provider.
This step depends on your Identity Provider choice and is not covered here.

Configure your Service Provider by editing ``/etc/shibboleth/shibboleth2.xml``
file. You are advised to examine `Shibboleth Service Provider Configuration documentation <https://wiki.shibboleth.net/confluence/display/SHIB2/Configuration>`_

Examine your attributes map file ``/etc/shibboleth/attributes-map.xml`` and adjust
to your requirements if needed. For more information see
`attributes documentation <https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPAddAttribute>`_

Once you are done, restart your shibboleth daemon::

    $ service shibd restart

Enable the ``OS-FEDERATION`` extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow the steps outlined at: `Enabling Federation Extension`_.

.. _`Enabling Federation Extension`: extensions/federation-configuration.html

Configuring Federation
----------------------

Now that the Identity Provider and Keystone are communicating we can start to
configure the ``OS-FEDERATION`` extension.

1. Add local Keystone groups and roles
2. Add Identity Provider(s), Mapping(s), and Protocol(s)

Create Keystone groups and assign roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned earlier, no new users will be added to the Identity backend, but
the Identity Service requires group-based role assignments to authorize
federated users. The federation mapping function will map the user into local
Identity Service groups objects, and thus to local role assignments.

Thus, it is required to create the necessary Identity Service groups that
correspond to the Identity Provider's groups; additionally, these groups should
be assigned roles on one or more projects or domains.

You may be interested in more information on `group management
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3.md#create-group-post-groups>`_
and `role assignments
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3.md#grant-role-to-group-on-project-put-projectsproject_idgroupsgroup_idrolesrole_id>`_,
both of which are exposed to the CLI via `python-openstackclient
<https://pypi.python.org/pypi/python-openstackclient/>`_.

Add Identity Provider(s), Mapping(s), and Protocol(s)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To utilize federation the following must be created in the Identity Service:

* Identity Provider
* Mapping
* Protocol

More information on ``OS-FEDERATION`` can be found `here
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md>`__.

~~~~~~~~~~~~~~~~~
Identity Provider
~~~~~~~~~~~~~~~~~

Create an Identity Provider object in Keystone, which represents the Identity
Provider we will use to authenticate end users.

More information on identity providers can be found `here
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#register-an-identity-provider-put-os-federationidentity_providersidp_id>`__.

~~~~~~~
Mapping
~~~~~~~
A mapping is simply a list of rules. The only Identity API objects that will support mapping are: group.

Mapping adds a set of rules to map federation protocol attributes to Identity API objects.
An Identity Provider has exactly one mapping specified per protocol.

Mapping objects can be used multiple times by different combinations of Identity Provider and Protocol.

More information on mapping can be found `here
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#create-a-mapping-put-os-federationmappingsmapping_id>`__.

~~~~~~~~
Protocol
~~~~~~~~

Contains information that dictates which Mapping rules to use for an incoming
request made by an IdP. An IdP may have multiple supported protocol.

Add `Protocol object
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#add-a-supported-protocol-and-attribute-mapping-combination-to-an-identity-provider-put-os-federationidentity_providersidp_idprotocolsprotocol_id>`__ and specify the mapping id
you want to use with the combination of the IdP and Protocol.

Performing federated authentication
-----------------------------------

1. Authenticate externally and generated an unscoped token in Keystone
2. Determine accessible resources
3. Get a scoped token

Get an unscoped token
~~~~~~~~~~~~~~~~~~~~~

Unlike other authentication methods in the Identity Service, the user does not
issue an HTTP POST request with authentication data in the request body. To
start federated authentication a user must access the dedicated URL with
Identity Provider's and Protocol's identifiers stored within a protected URL.
The URL has a format of:
``/v3/OS-FEDERATION/identity_providers/{identity_provider}/protocols/{protocol}/auth``.

In this instance we follow a standard SAML2 authentication procedure, that is,
the user will be redirected to the Identity Provider's authentication webpage
and be prompted for credentials. After successfully authenticating the user
will be redirected to the Service Provider's endpoint. If using a web browser,
a token will be returned in XML format.

In the returned unscoped token, a list of Identity Service groups the user
belongs to will be included.

More information on getting an unscoped token can be found `here
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#authenticating>`__.

Determine accessible resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By using the previously returned token, the user can issue requests to the list
projects and domains that are accessible.

* List projects a federated user can access: ``GET /OS-FEDERATION/projects``
* List domains a federated user can access: ``GET /OS-FEDERATION/domains``

More information on listing resources can be found `here
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#listing-projects-and-domains>`__.

Get a scoped token
~~~~~~~~~~~~~~~~~~

A federated user may request a scoped token, by using the unscoped token. A
project or domain may be specified by either ``id`` or ``name``. An ``id`` is
sufficient to uniquely identify a project or domain.

More information on getting a scoped token can be found `here
<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#request-a-scoped-os-federation-token-post-authtokens>`__.
