==================
Federated Identity
==================

-----------
Definitions
-----------
* `Service Provider (SP)`: provides a service to an end-user.
* `Identity Provider (IdP)`: service that stores information about users and
  groups.
* `SAML assertion`: contains information about a user as provided by an IdP.

You can use federation for the Identity service (keystone) in two ways:

* Supporting keystone as a :abbr:`SP (Service Provider)`: consuming identity
  assertions issued by an external Identity Provider, such as SAML
  assertions or OpenID Connect claims.
* Supporting keystone as an :abbr:`IdP (Identity Provider)`: fulfilling
  authentication requests on behalf of Service Providers.

  .. note::

      It is also possible to have one keystone act as an SP that
      consumes Identity from another keystone acting as an IdP.

There is currently support for two major federation protocols:

* `SAML <https://en.wikipedia.org/wiki/SAML_2.0>`_
* `OpenID Connect <https://en.wikipedia.org/wiki/OpenID_Connect>`_

.. figure:: figures/keystone-federation.png
   :width: 100%

   Keystone federation

To enable federation:

#. Run keystone under Apache. See `Configure the Apache HTTP server
   <https://docs.openstack.org/ocata/install-guide-obs/keystone-install.html>`_
   for more information.

   .. note::

      Other application servers, such as `nginx <https://www.nginx.com/resources/wiki>`_,
      have support for federation extensions that may work but are not tested
      by the community.

#. Configure Apache to use a federation capable module.
   We recommend Shibboleth, see :doc:`the Shibboleth documentation<../advanced-topics/federation/shibboleth>` for more information.

   .. note::

      Another option is ``mod_auth_melon``, see `the mod's github repo <https://github.com/UNINETT/mod_auth_mellon>`_
      for more information.

#. Configure federation in keystone.

.. note::

   The external IdP is responsible for authenticating users and communicates
   the result of authentication to keystone using authentication assertions.
   Keystone maps these values to keystone user groups and assignments
   created in keystone.

Support keystone as a SP
~~~~~~~~~~~~~~~~~~~~~~~~

To have keystone as an SP, you will need to configure
keystone to accept assertions from external IdPs. Examples of external
IdPs are:

* :abbr:`ADFS (Active Directory Federation Services)`
* FreeIPA
* Tivoli Access Manager
* Keystone

Configure federation in keystone
--------------------------------

#. Configure authentication drivers in ``keystone.conf`` by adding the
   authentication methods to the ``[auth]`` section in ``keystone.conf``.
   Ensure the names are the same as to the protocol names added via Identity
   API v3.

   For example:

   .. code-block:: ini

      [auth]
      methods = external,password,token,saml2,openid

   .. note::

      ``saml2`` and ``openid`` are instances of the ``mapped`` plugin. These
      must match the name of the of the federation protocol created via the
      Identity API. The other names in the example are not related to
      federation.

#. Create local keystone groups and assign roles.

   .. important::

      The keystone requires group-based role assignments to authorize
      federated users. The federation mapping engine maps federated users into
      local user groups, which are the actors in keystone's role assignments.

#. Create an IdP object in keystone. The object must represent the
   IdP you will use to authenticate end users:

   .. code:: ini

      PUT /OS-FEDERATION/identity_providers/{idp_id}

   More configuration information for IdPs can be found `Register an Identity Provider <https://developer.openstack.org/api-ref/identity/v3-ext/index.html#register-an-identity-provider>`_.

#. Add mapping rules:

   .. code:: ini

      PUT /OS-FEDERATION/mappings/{mapping_id}

   More configuration information for mapping rules can be found `Create a mapping <https://developer.openstack.org/api-ref/identity/v3-ext/index.html#create-a-mapping>`_.

   .. note::

       The only keystone API objects that support mapping are groups and users.

#. Add a protocol object and specify the mapping ID you want to use with the
   combination of the IdP and protocol:

   .. code:: ini

      PUT /OS-FEDERATION/identity_providers/{idp_id}/protocols/{protocol_id}

   More configuration information for protocols can be found `Add a protocol and attribute mapping to an identity provider <https://developer.openstack.org/api-ref/identity/v3-ext/index.html#add-a-protocol-and-attribute-mapping-to-an-identity-provider>`_.

Perform federated authentication
--------------------------------

#. Authenticate externally and generate an unscoped token in keystone:

   .. note::

      Unlike other authentication methods in keystone, the user does
      not issue an HTTP POST request with authentication data in the request body.
      To start federated authentication a user must access the dedicated URL with
      IdP's and protocol's identifiers stored within a protected URL.
      The URL has a format of:
      ``/v3/OS-FEDERATION/identity_providers/{idp_id}/protocols/{protocol_id}/auth``.

   .. code:: ini

      GET/POST /OS-FEDERATION/identity_providers/{identity_provider}/protocols/{protocol}/auth

#. Determine accessible resources. By using the previously returned token, the
   user can issue requests to the list projects and domains that are
   accessible.

   * List projects a federated user can access: GET /OS-FEDERATION/projects
   * List domains a federated user can access: GET /OS-FEDERATION/domains

   .. code:: ini

      GET /OS-FEDERATION/projects

#. Get a scoped token. A federated user can request a scoped token using
   the unscoped token. A project or domain can be specified by either ID or
   name. An ID is sufficient to uniquely identify a project or domain.

   .. code:: ini

      POST /auth/tokens

Support keystone as an IdP
~~~~~~~~~~~~~~~~~~~~~~~~~~

When acting as an IdP, the primary role of keystone is
to issue assertions about users owned by keystone. This is done using PySAML2.

Configure federation in keystone
--------------------------------

There are certain settings in ``keystone.conf`` that must be set up, prior
to attempting to federate multiple keystone deployments.

#. Within ``keystone.conf``, assign values to the ``[saml]``
   related fields, for example:

   .. code:: ini

      [saml]
      certfile=/etc/keystone/ssl/certs/ca.pem
      keyfile=/etc/keystone/ssl/private/cakey.pem
      idp_entity_id=https://keystone.example.com/v3/OS-FEDERATION/saml2/idp
      idp_sso_endpoint=https://keystone.example.com/v3/OS-FEDERATION/saml2/sso
      idp_metadata_path=/etc/keystone/saml2_idp_metadata.xml

#. We recommend the following `Organization` configuration options.
   Ensure these values contain not special characters that may cause
   problems as part of a URL:

   .. code:: ini

      idp_organization_name=example_company
      idp_organization_display_name=Example Corp.
      idp_organization_url=example.com

#. As with the `Organization` options, the `Contact` options are not
   necessary, but it is advisable to set these values:

   .. code:: ini

      idp_contact_company=example_company
      idp_contact_name=John
      idp_contact_surname=Smith
      idp_contact_email=jsmith@example.com
      idp_contact_telephone=555-55-5555
      idp_contact_type=technical

Generate metadata
-----------------

Metadata must be exchanged to create a trust between the IdP and the SP.

#. Create metadata for your keystone IdP, run the ``keystone-manage`` command
   and pipe the output to a file. For example:

   .. code:: console

      $ keystone-manage saml_idp_metadata > /etc/keystone/saml2_idp_metadata.xml

   .. note::

      The file location must match the value of the ``idp_metadata_path``
      configuration option assigned previously.

Create a SP
-----------

To setup keystone-as-a-Service-Provider properly, you will need to
understand what protocols are supported by external IdPs.
For example, keystone as an SP can allow identities to federate in from a
ADFS IdP but it must be configured to understand the SAML v2.0 protocol.
ADFS issues assertions using SAML v2.0. Some examples
of federated protocols include:

* SAML v2.0
* OpenID Connect

The following instructions are an example of how you can configure
keystone as an SP.

#. Create a new SP with an ID of BETA.

#. Create a ``sp_url`` of `<http://beta.example.com/Shibboleth.sso/SAML2/ECP>`_.

#. Create a ``auth_url`` of `<http://beta.example.com:5000/v3/OS-FEDERATION/identity_providers/beta/protocols/saml2/auth>`_.

   .. note::

      Use the ``sp_url`` when creating a SAML assertion for BETA and signed by
      the current keystone IdP. Use the ``auth_url`` when retrieving the token
      for BETA once the SAML assertion is sent.

#. Set the ``enabled`` field to ``true``. It is set to
   ``false`` by default.

#. Your output should reflect the following example:

   .. code:: console

      $ curl -s -X PUT \
     -H "X-Auth-Token: $OS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"service_provider": {"auth_url": "http://beta.example.com:5000/v3/OS-FEDERATION/identity_providers/beta/protocols/saml2/auth", "sp_url": "https://example.com:5000/Shibboleth.sso/SAML2/ECP", "enabled": true}}' \
     http://localhost:5000/v3/OS-FEDERATION/service_providers/BETA | python -mjson.tool

keystone-to-keystone
~~~~~~~~~~~~~~~~~~~~

Keystone acting as an IdP is known as :abbr:`k2k (keystone-2-keystone)`
or k2k federation, where a keystone somewhere is acting as the SP
and another keystone is acting as the IdP. All IdPs issue
assertions about the identities it owns using a `Protocol`.

Test it all out
---------------

Use keystoneauth to create a password session with the IdP, then use the
session to authenticate with the SP, and get a scoped token from the SP.

.. NOTE::
    ECP stands for Enhanced Client or Proxy, an extension from the SAML2
    protocol used in non-browser interfaces, like in the following example.

.. code-block:: python

    import os

    from keystoneauth1 import session
    from keystoneauth1.identity import v3
    from keystoneauth1.identity.v3 import k2k

    auth = v3.Password(auth_url=os.environ.get('OS_AUTH_URL'),
                       username=os.environ.get('OS_USERNAME'),
                       password=os.environ.get('OS_PASSWORD'),
                       user_domain_name=os.environ.get('OS_USER_DOMAIN_NAME'),
                       project_name=os.environ.get('OS_PROJECT_NAME'),
                       project_domain_name=os.environ.get('OS_PROJECT_DOMAIN_NAME'))
    password_session = session.Session(auth=auth)
    k2ksession = k2k.Keystone2Keystone(password_session.auth, 'mysp',
                                       domain_name='federated_domain')
    auth_ref = k2ksession.get_auth_ref(password_session)
    scoped_token_id = auth_ref.auth_token
    print('Scoped token id: %s' % scoped_token_id)

Mapping rules
~~~~~~~~~~~~~

Mapping adds a set of rules to map federation attributes to keystone users
or groups. An IdP has exactly one mapping specified per protocol.

A mapping is a translation between assertions provided from an IdP and
the permission and roles applied by an SP. Given an assertion from an IdP, an
SP applies a mapping to translate attributes from the
IdP to known roles. A mapping is typically
owned by an SP.

Mapping objects can be used multiple times by different combinations
of IdP and protocol.

A rule hierarchy is as follows:

.. code:: ini

   {
        "rules": [
           {
               "local": [
                  {
                       "<user> or <group>"
                   }
               ],
               "remote": [
                   {
                       "<condition>"
                   }
               ]
           }
       ]
   }

* ``rules``: top-level list of rules.
* ``local``: a rule containing information on what local attributes
  will be mapped.
* ``remote``: a rule containing information on what remote attributes will
  be mapped.
* ``condition``: contains information on conditions that allow a rule, can
  only be set in a remote rule.

For more information on mapping rules, see `Mapping Rules
<https://docs.openstack.org/keystone/latest/advanced-topics/federation/federated_identity.html#mapping-rules>`_.

Mapping creation
----------------

Mapping creation starts with the communication between the IdP and SP.
The IdP usually provides a set of assertions that their users
have in their assertion document. The SP will have to map
those assertions to known groups and roles.
For example:

.. code:: ini

   Identity Provider 1:
     name: jsmith
     groups: hacker
     other: <assertion information>
   The Service Provider may have 3 groups:
     Admin Group
     Developer Group
     User Group

   The mapping created by the Service Provider might look like:
     Local:
     Group: Developer Group
   Remote:
     Groups: hackers

The ``Developer Group`` may have a role assignment on the
``Developer Project``. When `jsmith` authenticates against IdP 1, it
presents that assertion to the SP.The SP maps the `jsmith` user to the
``Developer Group`` because the assertion says `jsmith` is a member of
the ``hacker`` group.

Mapping examples
----------------

A bare bones mapping is sufficient if you would like all federated users to
have the same authorization in the SP cloud. However, mapping is
quite powerful and flexible. You can map different remote
users into different user groups in keystone, limited only by the number of
assertions your IdP makes about each user.

A mapping is composed of a list of rules, and each rule is further composed of
a list of remote attributes and a list of local attributes. If a rule is
matched, all of the local attributes are applied in the SP. For a
rule to match, all of the remote attributes it defines must match.

In the base case, a federated user simply needs an assertion containing
an email address to be identified in the SP cloud. To achieve that, only
one rule is needed that requires the presence of one remote attribute:

.. code:: javascript

    {
        "rules": [
            {
                "remote": [
                    {
                        "type": "Email"
                    }
                ],
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        }
                    }
                ]
            }
        ]
    }

However, that is not particularly useful as the federated user would receive no
authorization. To rectify it, you can map all federated users with email
addresses into a ``federated-users`` group in the ``default`` domain. All
federated users will then be able to consume whatever role assignments that
user group has already received in keystone:

.. note::

   In this example, there is only one rule requiring one remote attribute.

.. code:: javascript

    {
        "rules": [
            {
                "remote": [
                    {
                        "type": "Email"
                    }
                ],
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        }
                    },
                    {
                        "group": {
                            "domain": {
                                "id": "0cd5e9"
                            },
                            "name": "federated-users"
                        }
                    }
                ]
            }
        ]
    }

This example can be expanded by adding a second rule that conveys
additional authorization to only a subset of federated users. Federated users
with a `title` attribute that matches either ``Manager`` or
``Supervisor`` are granted the hypothetical ``observer`` role, which would
allow them to perform any read-only API call in the cloud:

.. code:: javascript

    {
        "rules": [
            {
                "remote": [
                    {
                        "type": "Email"
                    },
                ],
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        }
                    },
                    {
                        "group": {
                            "domain": {
                                "id": "default"
                            },
                            "name": "federated-users"
                        }
                    }
                ]
            },
            {
                "remote": [
                    {
                        "type": "Title",
                        "any_one_of": [".*Manager$", "Supervisor"],
                        "regex": "true"
                    },
                ],
                "local": [
                    {
                        "group": {
                            "domain": {
                                "id": "default"
                            },
                            "name": "observers"
                        }
                    }
                ]
            }
        ]
    }

.. note::

   ``any_one_of`` and ``regex`` in the rule above map federated users into
   the ``observers`` group when a user's ``Title`` assertion matches any of
   the regular expressions specified in the ``any_one_of`` attribute.

Keystone also supports the following:

* ``not_any_of``, matches any assertion that does not include one of
  the specified values
* ``blacklist``, matches all assertions of the specified type except
  those included in the specified value
* ``whitelist`` does not match any assertion except those listed in the
  specified value.

Auto-Provisioning
-----------------

The mapping engine has the ability to aid in the auto-provisioning of resources
when a federated user authenticates for the first time. This can be achieved
using a specific mapping syntax that the mapping engine can parse and
ultimately make decisions on.

For example, consider the following mapping:

.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        }
                    },
                    {
                        "projects": [
                            {
                                "name": "Production",
                                "roles": [
                                    {
                                        "name": "observer"
                                    }
                                ]
                            },
                            {
                                "name": "Staging",
                                "roles": [
                                    {
                                        "name": "member"
                                    }
                                ]
                            },
                            {
                                "name": "Project for {0}",
                                "roles": [
                                    {
                                        "name": "admin"
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "remote": [
                    {
                        "type": "UserName"
                    }
                ]
            }
        ]
    }

The semantics of the ``remote`` section have not changed. The difference
between this mapping and the other examples is the addition of a ``projects``
section within the ``local`` rules. The ``projects`` list supplies a list
of projects that the federated user will be given access to. The projects
will be automatically created if they don't exist when the user
authenticated and the mapping engine has applied values from the assertion
and mapped them into the ``local`` rules.

In the above example, an authenticated federated user will be granted the
``observer`` role on the ``Production`` project, ``member`` role on the
``Staging`` project, and they will have ``admin`` role on the ``Project for
jsmith``.

It is important to note the following constraints apply when auto-provisioning:

* Projects are the only resource that will be created dynamically.
* Projects will be created within the domain associated with the Identity
  Provider.
* The ``projects`` section of the mapping must also contain a ``roles``
  section.

  + Roles within the project must already exist in the deployment or domain.

* Assignments are actually created for the user which is unlike the
  ephemeral group memberships.

Since the creation of roles typically requires policy changes across other
services in the deployment, it is expected that roles are created ahead of
time. Federated authentication should also be considered idempotent if the
attributes from the SAML assertion have not changed. In the example from above,
if the user's name is still ``jsmith``, then no new projects will be
created as a result of authentication.

Mappings can be created that mix ``groups`` and ``projects`` within the
``local`` section. The mapping shown in the example above does not contain a
``groups`` section in the ``local`` rules. This will result in the federated
user having direct role assignments on the projects in the ``projects`` list.
The following example contains ``local`` rules comprised of both ``projects``
and ``groups``, which allow for direct role assignments and group memberships.

.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        }
                    },
                    {
                        "projects": [
                            {
                                "name": "Marketing",
                                "roles": [
                                    {
                                        "name": "member"
                                    }
                                ]
                            },
                            {
                                "name": "Development project for {0}",
                                "roles": [
                                    {
                                        "name": "admin"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "group": {
                            "name": "Finance",
                            "domain": {
                                "id": "6fe767"
                            }
                        }
                    }
                ],
                "remote": [
                    {
                        "type": "UserName"
                    }
                ]
            }
        ]
    }

In the above example, a federated user will receive direct role assignments on
the ``Marketing`` project, as well as a dedicated project specific to the
federated user's name. In addition to that, they will also be placed in the
``Finance`` group and receive all role assignments that group has on projects
and domains.

Setup Mellon
============

------------------------------------------
Configure Apache HTTPD for mod_auth_mellon
------------------------------------------

Follow the steps outlined at: Keystone install guide for `SUSE`_, `RedHat`_ or
`Ubuntu`_.

.. _`SUSE`: ../../install/keystone-install-obs.html#configure-the-apache-http-server
.. _`RedHat`: ../../install/keystone-install-rdo.html#configure-the-apache-http-server
.. _`Ubuntu`: ../../install/keystone-install-ubuntu.html#configure-the-apache-http-server

You'll also need to install the Apache module `mod_auth_mellon
<https://github.com/UNINETT/mod_auth_mellon>`_.  For example:

.. code-block:: bash

    $ apt-get install libapache2-mod-auth-mellon

Configure your Keystone virtual host and adjust the config to properly handle SAML2 workflow:

Add this *WSGIScriptAlias* directive to your public vhost configuration::

    WSGIScriptAliasMatch ^(/v3/OS-FEDERATION/identity_providers/.*?/protocols/.*?/auth)$ /usr/local/bin/keystone-wsgi-public/$1

Make sure the *wsgi-keystone.conf* contains a *<Location>* directive for the Mellon module and
a *<Location>* directive for each identity provider

.. code-block:: none

    <Location /v3>
        MellonEnable "info"
        MellonSPPrivateKeyFile /etc/apache2/mellon/http_keystone.fqdn.key
        MellonSPCertFile /etc/apache2/mellon/http_keystone.fqdn.cert
        MellonSPMetadataFile /etc/apache2/mellon/http_keystone.fqdn.xml
        MellonIdPMetadataFile /etc/apache2/mellon/idp-metadata.xml
        MellonEndpointPath /v3/OS-FEDERATION/identity_providers/myidp/protocols/saml2/auth/mellon
        MellonIdP "IDP"
    </Location>

    <Location /v3/OS-FEDERATION/identity_providers/myidp/protocols/saml2/auth>
        AuthType "Mellon"
        MellonEnable "auth"
    </Location>

.. NOTE::
    * See below for information about how to generate the values for the
      `MellonSPMetadataFile`, etc. directives.
    * ``saml2`` is the name of the `protocol that you will configure <configure_federation.html#protocol>`_
    * ``myidp`` is the name associated with the `IdP in Keystone <configure_federation.html#identity_provider>`_
    * You are advised to carefully examine `mod_auth_mellon Apache
      configuration documentation
      <https://github.com/UNINETT/mod_auth_mellon>`_

Enable the ``auth_mellon`` module, for example:

.. code-block:: bash

    $ a2enmod auth_mellon

----------------------------------
Configuring the Mellon SP Metadata
----------------------------------

Mellon provides a script called `mellon_create_metadata.sh`_ which generates
the values for the config directives `MellonSPPrivateKeyFile`,
`MellonSPCertFile`, and `MellonSPMetadataFile`.  It is run like this:

.. code-block:: bash

    $ ./mellon_create_metadata.sh http://keystone.fqdn:5000 \
      http://keystone.fqdn:5000/v3/OS-FEDERATION/identity_providers/myidp/protocols/saml2/auth/mellon

The first parameter is used as the entity ID, a unique identifier for this
Keystone SP.  You do not have to use the URL, but it is an easy way to uniquely
identify each Keystone SP.  The second parameter is the full URL for the
endpoint path corresponding to the parameter `MellonEndpointPath`. Note that
the metadata generated by this script includes a signing key but not an
encryption key, and your IdP (such as testshib.org) may require an encryption
key. Simply change the node `<KeyDescriptor use="signing">` to
`<KeyDescriptor use="encryption">` or add another key to the file. Check your
IdP documentation for details.

After generating the keypair and metadata, copy the files to the locations
given in the Mellon directives in your apache configs.

Upload the Service Provider's Metadata file which you just generated to your
Identity Provider. This is the file used as the value of the
`MellonSPMetadataFile` in the config. The IdP may provide a webpage where you
can upload the file, or you may be required to submit the file using `wget` or
`curl`. Please check your IdP documentation for details.

Fetch your Identity Provider's Metadata file and copy it to the path specified
by the `MellonIdPMetadataFile` directive above. For example:

.. code-block:: bash

    $ wget --cacert /path/to/ca.crt -O /etc/apache2/mellon/idp-metadata.xml \
      https://idp.fqdn/idp/saml2/metadata

Once you are done, restart the Apache instance that is serving Keystone, for example:

.. code-block:: bash

    $ service apache2 restart

.. _`mellon_create_metadata.sh`: https://github.com/UNINETT/mod_auth_mellon/blob/master/mellon_create_metadata.sh

Setup OpenID Connect
====================

----------------------------
Configuring mod_auth_openidc
----------------------------

Federate Keystone (SP) and an external IdP using OpenID Connect (`mod_auth_openidc`_)

.. _`mod_auth_openidc`: https://github.com/pingidentity/mod_auth_openidc

To install `mod_auth_openidc` on Ubuntu, perform the following:

.. code-block:: bash

  $ sudo apt-get install libapache2-mod-auth-openidc

This module is available for other distributions (Fedora/CentOS/Red Hat) from:
https://github.com/pingidentity/mod_auth_openidc/releases

Enable the auth_openidc module:

.. code-block:: bash

   $ sudo a2enmod auth_openidc

In the keystone vhost file, locate the virtual host entry and add the following
entries for OpenID Connect:

.. code-block:: none

  <VirtualHost *:5000>

      ...

      OIDCClaimPrefix "OIDC-"
      OIDCResponseType "id_token"
      OIDCScope "openid email profile"
      OIDCProviderMetadataURL <url_of_provider_metadata>
      OIDCClientID <openid_client_id>
      OIDCClientSecret <openid_client_secret>
      OIDCCryptoPassphrase openstack
      OIDCRedirectURI http://localhost:5000/v3/OS-FEDERATION/identity_providers/<idp_id>/protocols/openid/auth

      <LocationMatch /v3/OS-FEDERATION/identity_providers/.*?/protocols/openid/auth>
        AuthType openid-connect
        Require valid-user
        LogLevel debug
      </LocationMatch>
  </VirtualHost>

Note an example of an `OIDCProviderMetadataURL` instance is: https://accounts.google.com/.well-known/openid-configuration
If not using `OIDCProviderMetadataURL`, then the following attributes
must be specified: `OIDCProviderIssuer`, `OIDCProviderAuthorizationEndpoint`,
`OIDCProviderTokenEndpoint`, `OIDCProviderTokenEndpointAuth`,
`OIDCProviderUserInfoEndpoint`, and `OIDCProviderJwksUri`

Note, if using a mod_wsgi version less than 4.3.0, then the `OIDCClaimPrefix`
must be specified to have only alphanumerics or a dash ("-"). This is because
mod_wsgi blocks headers that do not fit this criteria. See http://modwsgi.readthedocs.org/en/latest/release-notes/version-4.3.0.html#bugs-fixed
for more details

Once you are done, restart your Apache daemon:

.. code-block:: bash

    $ sudo service apache2 restart

----
Tips
----

1. When creating a `mapping`_, note that the 'remote' attributes will be prefixed,
   with `HTTP_`, so for instance, if you set OIDCClaimPrefix to `OIDC-`, then a
   typical remote value to check for is: `HTTP_OIDC_ISS`.

2. Don't forget to add openid as an [auth] plugin in keystone.conf, see
   `Configure authentication drivers in keystone.conf`_

.. _`Configure authentication drivers in keystone.conf`: federated_identity.html#configure-authentication-drivers-in-keystone-conf
.. _`mapping`: configure_federation.html#mapping

Setup Shibboleth
================

-----------------------------------------
Configure Apache HTTPD for mod_shibboleth
-----------------------------------------

Follow the steps outlined at: Running Keystone in HTTPD for `SUSE`_, `RedHat`_
or `Ubuntu`_.

.. _`SUSE`: ../../install/keystone-install-obs.html#configure-the-apache-http-server
.. _`RedHat`: ../../install/keystone-install-rdo.html#configure-the-apache-http-server
.. _`Ubuntu`: ../../install/keystone-install-ubuntu.html#configure-the-apache-http-server

You'll also need to install `Shibboleth <https://wiki.shibboleth.net/confluence/display/SHIB2/Home>`_, for
example:

.. code-block:: bash

    $ apt-get install libapache2-mod-shib2

Configure your Keystone virtual host and adjust the config to properly handle SAML2 workflow:

Add this *WSGIScriptAliasMatch* directive to your public vhost configuration::

    WSGIScriptAliasMatch ^(/v3/OS-FEDERATION/identity_providers/.*?/protocols/.*?/auth)$ /usr/local/bin/keystone-wsgi-public/$1

Make sure the *keystone.conf* vhost file contains a *<Location>* directive for the Shibboleth module and
a *<Location>* directive for each identity provider::

    <Location /Shibboleth.sso>
        SetHandler shib
    </Location>

    <Location /v3/OS-FEDERATION/identity_providers/myidp/protocols/saml2/auth>
        ShibRequestSetting requireSession 1
        AuthType shibboleth
        ShibExportAssertion Off
        Require valid-user

        <IfVersion < 2.4>
            ShibRequireSession On
            ShibRequireAll On
       </IfVersion>
    </Location>

.. NOTE::
    * ``saml2`` is the name of the `protocol that you will configure <configure_federation.html#protocol>`_
    * ``myidp`` is the name associated with the `IdP in Keystone <configure_federation.html#identity_provider>`_
    * The ``ShibRequireSession`` and ``ShibRequireAll`` rules are invalid in
      Apache 2.4+.
    * You are advised to carefully examine `Shibboleth Apache configuration
      documentation
      <https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPApacheConfig>`_

Enable the ``shib2`` module, for example:

.. code-block:: bash

    $ a2enmod shib2

Restart Apache, for example:

.. code-block:: bash

    $ service apache2 restart

---------------------------
Configuring shibboleth2.xml
---------------------------

Once you have your Keystone vhost (virtual host) ready, it's then time to
configure Shibboleth and upload your Metadata to the Identity Provider.

Create a new keypair for Shibboleth with:

.. code-block:: bash

    $ shib-keygen -y <number of years>

The newly created key file will be stored under ``/etc/shibboleth/sp-key.pem``.

Configure your Service Provider by editing ``/etc/shibboleth/shibboleth2.xml``
file. You will want to change five settings:

* Set the SP entity ID. This value usually has the form of a URI but it does not
  have to resolve to anything. It must uniquely identify your Service Provider
  to your Identity Provider.

.. code-block:: xml

    <ApplicationDefaults entityID="http://mysp.example.com/shibboleth">

* Set the IdP entity ID. This value is determined by the IdP. For example, if
  Keystone is the IdP:

.. code-block:: xml

    <SSO entityID="https://myidp.example.com/v3/OS-FEDERATION/saml2/idp">

Example if testshib.org is the IdP:

.. code-block:: xml

    <SSO entityID="https://idp.testshib.org/idp/shibboleth">

* Remove the discoveryURL lines unless you want to enable advanced IdP discovery.

* Add a MetadataProvider block. The URI given here is a real URL that Shibboleth
  will use to fetch metadata from the IdP. For example, if Keystone is the IdP:

.. code-block:: xml

    <MetadataProvider type="XML" uri="https://myidp.example.com:5000/v3/OS-FEDERATION/saml2/metadata"/>

Example if testshib.org is the IdP:

.. code-block:: xml

    <MetadataProvider type="XML" uri="http://www.testshib.org/metadata/testshib-providers.xml" />

You are advised to examine `Shibboleth Service Provider Configuration documentation <https://wiki.shibboleth.net/confluence/display/SHIB2/Configuration>`_

The result should look like (The example shown below is for reference only, not
to be used in a production environment):

.. code-block:: xml

    <SPConfig xmlns="urn:mace:shibboleth:2.0:native:sp:config"
        xmlns:conf="urn:mace:shibboleth:2.0:native:sp:config"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
        clockSkew="180">

        <!--
        By default, in-memory StorageService, ReplayCache, ArtifactMap, and SessionCache
        are used. See example-shibboleth2.xml for samples of explicitly configuring them.
        -->

        <!--
        To customize behavior for specific resources on Apache, and to link vhosts or
        resources to ApplicationOverride settings below, use web server options/commands.
        See https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPConfigurationElements for help.

        For examples with the RequestMap XML syntax instead, see the example-shibboleth2.xml
        file, and the https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPRequestMapHowTo topic.
        -->

        <!-- The ApplicationDefaults element is where most of Shibboleth's SAML bits are defined. -->
        <ApplicationDefaults entityID="https://mysp.example.com/shibboleth">

            <!--
            Controls session lifetimes, address checks, cookie handling, and the protocol handlers.
            You MUST supply an effectively unique handlerURL value for each of your applications.
            The value defaults to /Shibboleth.sso, and should be a relative path, with the SP computing
            a relative value based on the virtual host. Using handlerSSL="true", the default, will force
            the protocol to be https. You should also set cookieProps to "https" for SSL-only sites.
            Note that while we default checkAddress to "false", this has a negative impact on the
            security of your site. Stealing sessions via cookie theft is much easier with this disabled.
            -->
            <Sessions lifetime="28800" timeout="3600" relayState="ss:mem"
                      checkAddress="false" handlerSSL="false" cookieProps="http">

                <!--
                Configures SSO for a default IdP. To allow for >1 IdP, remove
                entityID property and adjust discoveryURL to point to discovery service.
                (Set discoveryProtocol to "WAYF" for legacy Shibboleth WAYF support.)
                You can also override entityID on /Login query string, or in RequestMap/htaccess.
                -->
                <SSO entityID="https://myidp.example.com/v3/OS-FEDERATION/saml2/idp">
                  SAML2 SAML1
                </SSO>

                <!-- SAML and local-only logout. -->
                <Logout>SAML2 Local</Logout>

                <!-- Extension service that generates "approximate" metadata based on SP configuration. -->
                <Handler type="MetadataGenerator" Location="/Metadata" signing="false"/>

                <!-- Status reporting service. -->
                <Handler type="Status" Location="/Status" acl="127.0.0.1 ::1"/>

                <!-- Session diagnostic service. -->
                <Handler type="Session" Location="/Session" showAttributeValues="false"/>

                <!-- JSON feed of discovery information. -->
                <Handler type="DiscoveryFeed" Location="/DiscoFeed"/>
            </Sessions>
            <!--
            Allows overriding of error template information/filenames. You can
            also add attributes with values that can be plugged into the templates.
            -->
            <Errors supportContact="root@localhost"
                helpLocation="/about.html"
                styleSheet="/shibboleth-sp/main.css"/>

            <!-- Example of remotely supplied batch of signed metadata. -->
            <!--
            <MetadataProvider type="XML" uri="http://federation.org/federation-metadata.xml"
                  backingFilePath="federation-metadata.xml" reloadInterval="7200">
                <MetadataFilter type="RequireValidUntil" maxValidityInterval="2419200"/>
                <MetadataFilter type="Signature" certificate="fedsigner.pem"/>
            </MetadataProvider>
            -->

            <!-- Example of locally maintained metadata. -->
            <!--
            <MetadataProvider type="XML" file="partner-metadata.xml"/>
            -->
            <MetadataProvider type="XML" uri="https://myidp.example.com:5000/v3/OS-FEDERATION/saml2/metadata"/>

            <!-- Map to extract attributes from SAML assertions. -->
            <AttributeExtractor type="XML" validate="true" reloadChanges="false" path="attribute-map.xml"/>

            <!-- Use a SAML query if no attributes are supplied during SSO. -->
            <AttributeResolver type="Query" subjectMatch="true"/>

            <!-- Default filtering policy for recognized attributes, lets other data pass. -->
            <AttributeFilter type="XML" validate="true" path="attribute-policy.xml"/>

            <!-- Simple file-based resolver for using a single keypair. -->
            <CredentialResolver type="File" key="sp-key.pem" certificate="sp-cert.pem"/>

            <!--
            The default settings can be overridden by creating ApplicationOverride elements (see
            the https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPApplicationOverride topic).
            Resource requests are mapped by web server commands, or the RequestMapper, to an
            applicationId setting.
            Example of a second application (for a second vhost) that has a different entityID.
            Resources on the vhost would map to an applicationId of "admin":
            -->
            <!--
            <ApplicationOverride id="admin" entityID="https://admin.example.org/shibboleth"/>
            -->
        </ApplicationDefaults>

        <!-- Policies that determine how to process and authenticate runtime messages. -->
        <SecurityPolicyProvider type="XML" validate="true" path="security-policy.xml"/>

        <!-- Low-level configuration about protocols and bindings available for use. -->
        <ProtocolProvider type="XML" validate="true" reloadChanges="false" path="protocols.xml"/>

    </SPConfig>

If keystone is your IdP, you will need to examine your attributes map file
``/etc/shibboleth/attribute-map.xml`` and add the following attributes:

.. code-block:: xml

    <Attribute name="openstack_user" id="openstack_user"/>
    <Attribute name="openstack_roles" id="openstack_roles"/>
    <Attribute name="openstack_project" id="openstack_project"/>
    <Attribute name="openstack_user_domain" id="openstack_user_domain"/>
    <Attribute name="openstack_project_domain" id="openstack_project_domain"/>

For more information see the
`attributes documentation <https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPAddAttribute>`_

Once you are done, restart your Shibboleth daemon and apache:

.. _`external authentication`: ../external-auth.html

.. code-block:: bash

    $ service shibd restart
    $ service apache2 restart

Check ``/var/log/shibboleth/shibd_warn.log`` for any ERROR or CRIT notices and
correct them.

Upload your Service Provider's metadata file to your Identity Provider. You can
fetch it with:

.. code-block:: bash

    $ wget http://mysp.example.com/Shibboleth.sso/Metadata

This step depends on your Identity Provider choice and is not covered here.
If keystone is your Identity Provider you do not need to upload this file.

Setup Web Single Sign-On (SSO)
==============================

----------------
Keystone Changes
----------------

1. Update `trusted_dashboard` in keystone.conf.

Specify URLs of trusted horizon servers. This value may be repeated
multiple times. This setting ensures that keystone only sends token data back
to trusted servers. This is performed as a precaution, specifically to
prevent man-in-the-middle (MITM) attacks.

.. code-block:: ini

  [federation]
  trusted_dashboard = http://acme.horizon.com/auth/websso/
  trusted_dashboard = http://beta.horizon.com/auth/websso/

2. Update httpd vhost file with websso information.

The `/v3/auth/OS-FEDERATION/websso/<protocol>` and
`/v3/auth/OS-FEDERATION/identity_providers/{idp_id}/protocols/{protocol_id}/websso`
routes must be protected by the chosen httpd module. This is performed so the
request that originates from horizon will use the same identity provider that
is configured in keystone.

.. WARNING::
    By using the IdP specific route, a user will no longer leverage the Remote
    ID of a specific Identity Provider, and will be unable to verify that the
    Identity Provider is trusted, the mapping will remain as the only means to
    controlling authorization.

If `mod_shib` is used, then use the following as an example:

.. code-block:: none

  <VirtualHost *:5000>

      ...

      <Location ~ "/v3/auth/OS-FEDERATION/websso/saml2">
        AuthType shibboleth
        Require valid-user
        ShibRequestSetting requireSession 1
        ShibRequireSession On
        ShibExportAssertion Off
      </Location>
      <Location ~ "/v3/auth/OS-FEDERATION/identity_providers/myidp/protocols/saml2/websso">
        AuthType shibboleth
        Require valid-user
      </Location>
  </VirtualHost>

If `mod_auth_openidc` is used, then use the following as an example:

.. code-block:: none

  <VirtualHost *:5000>

      OIDCRedirectURI http://localhost:5000/v3/auth/OS-FEDERATION/websso
      OIDCRedirectURI http://localhost:5000/v3/auth/OS-FEDERATION/identity_providers/myidp/protocols/openid/websso

      ...

      <Location ~ "/v3/auth/OS-FEDERATION/websso/openid">
        AuthType openid-connect
        Require valid-user
        ...
      </Location>
      <Location ~ "/v3/auth/OS-FEDERATION/identity_providers/myidp/protocols/openid/websso">
        AuthType openid-connect
        Require valid-user
        ...
      </Location>
  </VirtualHost>

If `mod_auth_kerb` is used, then use the following as an example:

.. code-block:: none

  <VirtualHost *:5000>

      ...

      <Location ~ "/v3/auth/OS-FEDERATION/websso/kerberos">
        AuthType Kerberos
        AuthName "Acme Corporation"
        KrbMethodNegotiate on
        KrbMethodK5Passwd off
        Krb5Keytab /etc/apache2/http.keytab
        ...
      </Location>
      <Location ~ "/v3/auth/OS-FEDERATION/identity_providers/myidp/protocols/kerberos/websso">
        AuthType Kerberos
        AuthName "Acme Corporation"
        KrbMethodNegotiate on
        KrbMethodK5Passwd off
        Krb5Keytab /etc/apache2/http.keytab
        ...
      </Location>
  </VirtualHost>

If `mod_auth_mellon` is used, then use the following as an example:

.. code-block:: none

  <VirtualHost *:5000>

      ...

      <Location ~ "/v3/auth/OS-FEDERATION/websso/saml2">
        AuthType Mellon
        MellonEnable auth
        Require valid-user
        ...
      </Location>
      <Location ~ "/v3/auth/OS-FEDERATION/identity_providers/myidp/protocols/saml2/websso">
        AuthType Mellon
        MellonEnable auth
        Require valid-user
        ...
      </Location>
  </VirtualHost>

.. NOTE::
    If you are also using SSO via the API, don't forget to make the Location
    settings match your configuration used for the keystone identity provider
    location:
    `/v3/OS-FEDERATION/identity_providers/<idp>/protocols/<protocol>/auth`

3. Update `remote_id_attribute` in keystone.conf.

A remote id attribute indicates the header to retrieve from the WSGI
environment. This header contains information about the identity
of the identity provider. For `mod_shib` this would be
``Shib-Identity-Provider``, for `mod_auth_openidc`, this could be
``HTTP_OIDC_ISS``.  For `mod_auth_mellon`, this could be ``MELLON_IDP``.

It is recommended that this option be set on a per-protocol basis.

.. code-block:: ini

  [saml2]
  remote_id_attribute = Shib-Identity-Provider
  [openid]
  remote_id_attribute = HTTP_OIDC_ISS

Alternatively, a generic option may be set at the `[federation]` level.

.. code-block:: ini

  [federation]
  remote_id_attribute = HTTP_OIDC_ISS

4. Copy the `sso_callback_template.html
<https://git.openstack.org/cgit/openstack/keystone/plain/etc/sso_callback_template.html>`__
template into the location specified by `[federation]/sso_callback_template`.

---------------
Horizon Changes
---------------

.. NOTE::

    Django OpenStack Auth version 1.2.0 or higher is required for these steps.

    Identity provider and federation protocol specific webSSO is only available
    in Django OpenStack Auth version 2.0.0 or higher.

1. Set the `WEBSSO_ENABLED` option.

Ensure the `WEBSSO_ENABLED` option is set to True in horizon's local_settings.py file,
this will provide users with an updated login screen for horizon.

.. code-block:: python

  WEBSSO_ENABLED = True

2. (Optional) Create a list of authentication methods with the
   `WEBSSO_CHOICES` option.

Within horizon's settings.py file, a list of supported authentication methods can be
specified. The list includes Keystone federation protocols such as OpenID Connect and
SAML, and also keys that map to specific identity provider and federation protocol
combinations (as defined in `WEBSSO_IDP_MAPPING`). With the exception of ``credentials``
which is reserved by horizon, and maps to the user name and password used by keystone's
identity backend.

.. code-block:: python

  WEBSSO_CHOICES = (
        ("credentials", _("Keystone Credentials")),
        ("openid", _("OpenID Connect")),
        ("saml2", _("Security Assertion Markup Language")),
        ("myidp_openid", "Acme Corporation - OpenID Connect"),
        ("myidp_saml2", "Acme Corporation - SAML2")
      )

3. (Optional) Create a dictionary of specific identity provider and federation
   protocol combinations.

A dictionary of specific identity provider and federation protocol combinations.
From the selected authentication mechanism, the value will be looked up as keys
in the dictionary. If a match is found, it will redirect the user to a identity
provider and federation protocol specific WebSSO endpoint in keystone, otherwise
it will use the value as the protocol_id when redirecting to the WebSSO by
protocol endpoint.

.. code-block:: python

  WEBSSO_IDP_MAPPING = {
        "myidp_openid": ("myidp", "openid"),
        "myidp_saml2": ("myidp", "saml2")
      }

.. NOTE::

    The value is expected to be a tuple formatted as: (<idp_id>, <protocol_id>).

6. (Optional) Specify an initial choice with the `WEBSSO_INITIAL_CHOICE`
   option.

The list set by the `WEBSSO_CHOICES` option will be generated in a drop-down
menu in the login screen. The setting `WEBSSO_INITIAL_CHOICE` will
automatically set that choice to be highlighted by default.

.. code-block:: python

  WEBSSO_INITIAL_CHOICE = "credentials"

7. Restart your web server:

.. code-block:: bash

   $ sudo service apache2 restart
