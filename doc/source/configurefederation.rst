..
      Copyright 2014 OpenStack, Foundation
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

===================================
Configuring Keystone for Federation
===================================

Definitions
-----------

* Service Provider (SP) - providing a service to an end-user
* Identity Provider (IdP) - server that stores information about users and groups
* SAML assertion - sent from an IdP, contains information about a user


Approach to Federation
---------------------------------
Support the use case where Keystone serves as a Service Provider, and an
external Identity Provider can send SAML assertions, once a user is 
authenticated.

There is no need to add any users to the Keystone backend. For authentication
we will rely on the Identity Provider via SAML assertions. For authorization,
we can only trust assignments created in Keystone.  


Prereqs
-------

Keystone must be ran under Apache, mod_shib (Apache module) handles the SAML2
handshake.

1) Run Keystone under Apache
2) Setup mod_shib
3) Enable OS-FEDERATION extension


Run Keystone under Apache
~~~~~~~~~~~~~~~~~~~~~~~~~

Prereq:
  apt-get apache2

Follow the steps outlined at: `Running Keystone in HTTPD`_.

.. _`Running Keystone in HTTPD`: apache-httpd.html

Additionally, before you starting apache, enable vhost and the shib2 and ssl modules:
* a2ensite wsgi-keystone.conf
* a2enmod ssl
* a2enmod shib2
* service apache2 restart


Setup mod_shib
~~~~~~~~~~~~~~

Prereq:
  apt-get libapache2-mod-shib2

Federate Keystone (SP) and an external IdP. Refer to `TestShib <http://www.testshib.org/install.html>`_


Enable OS-FEDERATION extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow the steps outlined at: `Enabling Federation Extension`_.

.. _`Enabling Federation Extension`: extensions/federation-configuration.html

Once you have your Keystone virtual host ready it’s time to configure
Shibboleth and upload your Metadata to the Identity Provider.

If new certificates are required, they can be easily created by executing:
shib-keygen -y <number of years>
The newly created file will be stored under /etc/shibboleth/sp-key.pem

If you are configuring it against testshib.org, there is a suggested `reading <https://openstack.local/Shibboleth.sso/Metadata>`_
on how to upload your SP’s Metadata into their system. This can be achieved
by executing:
wget --no-check-certificate -O <name of the file>

Next, upload your metadata file to testshib.org
You should be able to get customized shibboleth2.xml file, again from
testshib.org configuratin site. Save it as `/etc/shibboleth/shibboleth2.xml`

ATTENTION: remove `REMOTE_USER` from  `/etc/shibboleth/shibboleth2.x`


Configuring Federation
----------------------

Now that the Identity Provider and Keystone are communicating we can start to
configure the Federation Extension.

1) Add local Keystone groups and roles
2) Add Identity Provider/Mapping rules/Protocols
3) Get an unscoped token


Create Keystone groups and grant roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned earlier, no new users will be added to the Identity backend, but
the Identity Service requires to perform authorization. The federation mapping
function will map the user to local Identity Service groups objects.

Thus, it is required to create the necessary Identity Service groups, that
correspond to the Identity Provider's groups; additionally, these groups should
have roles on an Identity Service resource (project or domain).

More information on group management can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3.md#create-group-post-groups>`_
More information on grants can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3.md#grant-role-to-group-on-project-put-projectsproject_idgroupsgroup_idrolesrole_id>`_


Add Identity Provider/Mapping/Protocols
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To fully utilize federation the following entries must be created in the
Identity Service.

* Identity Provider
* Mapping
* Protocol

More information on federation can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md>`_

~~~~~~~~~~~~~~~~~
Identity Provider
~~~~~~~~~~~~~~~~~

Create an Identity Provider object in Keystone, it represents a trusted third
party service that is trusted by the Identity API to authenticate identities.

More information on mapping can be found here:
https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#register-an-identity-provider-put-os-federationidentity_providersidp_id

~~~~~~~
Mapping
~~~~~~~

Add a set of rules to map federation protocol attributes to Identity API objects.
An Identity Provider can have a single mapping specified per protocol.
A mapping is simply a list of rules. The only Identity API objects that will support mapping are: group.

More information on mapping can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#create-a-mapping-put-os-federationmappingsmapping_id>`_

~~~~~~~~
Protocol
~~~~~~~~

Contains information that dictates which Mapping rules to use for an incoming
request made by an IdP. An IdP may have multiple supported protocol.

More information on mapping can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#add-a-supported-protocol-and-attribute-mapping-combination-to-an-identity-provider-put-os-federationidentity_providersidp_idprotocolsprotocol_id>`_


Get an unscoped token
~~~~~~~~~~~~~~~~~~~~~

Unlike other authentication methods in the Identity Service, the user does not
issue an HTTP POST request with authentication data in the request body.
To start federated authentication a user must access the dedicated URL with
Identity Provider’s and Protocol’s identifiers stored within a protected URL.
The URL has a format of: /v3/OS-FEDERATION/identity_providers/{identity_provider}/protocols/{protocol}/auth.

In this instance we follow a standard SAML2 authentication procedure, that is,
the user will be redirected to the Identity Provider’s authentication webpage
and be prompted for credentials. After successfully authenticating the user
will be redirected to the Service Provider’s endpoint. If using a web browser,
a token will be returned in XML format.

In the returned unscoped token, a list of Identity Service groups the user
is a member of will be included.

More information getting an unscoped token can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#authenticating>`_

Determine accessible resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By using the previously returned token, the user can issue requests to
the list projects and domains that are accessible.

* List projects a federated user can access: GET /OS-FEDERATION/projects
* List domains a federated user can access: GET /OS-FEDERATION/domains

More information listing resources can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#listing-projects-and-domains>`_


Get a scoped token
~~~~~~~~~~~~~~~~~~

A federated user may request a scoped token, by using the unscoped token.
A project or domain may be specified by either id or name.
An id is sufficient to uniquely identify a project or domain.

More information getting an unscoped token can be found here: `<https://github.com/openstack/identity-api/blob/master/openstack-identity-api/v3/src/markdown/identity-api-v3-os-federation-ext.md#request-a-scoped-os-federation-token-post-authtokens>`_
