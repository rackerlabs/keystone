=====================================================
Additional configuration options for Identity service
=====================================================

The Identity service is configured in the ``/etc/keystone/keystone.conf`` file.

The following tables provide a comprehensive list of the Identity
service options.

.. include:: tables/keystone-assignment.inc
.. include:: tables/keystone-auth.inc
.. include:: tables/keystone-ca.inc
.. include:: tables/keystone-catalog.inc
.. include:: tables/keystone-common.inc
.. include:: tables/keystone-compliance.inc
.. include:: tables/keystone-credential.inc
.. include:: tables/keystone-debug.inc
.. include:: tables/keystone-domain.inc
.. include:: tables/keystone-federation.inc
.. include:: tables/keystone-fernet_tokens.inc
.. include:: tables/keystone-identity.inc
.. include:: tables/keystone-kvs.inc
.. include:: tables/keystone-ldap.inc
.. include:: tables/keystone-mapping.inc
.. include:: tables/keystone-memcache.inc
.. include:: tables/keystone-oauth.inc
.. include:: tables/keystone-os_inherit.inc
.. include:: tables/keystone-policy.inc
.. include:: tables/keystone-revoke.inc
.. include:: tables/keystone-role.inc
.. include:: tables/keystone-saml.inc
.. include:: tables/keystone-security.inc
.. include:: tables/keystone-token.inc
.. include:: tables/keystone-tokenless.inc
.. include:: tables/keystone-trust.inc
.. include:: tables/keystone-redis.inc

Domain-specific Identity drivers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Identity service supports domain-specific Identity drivers
installed on an SQL or LDAP back end, and supports domain-specific
Identity configuration options, which are stored in domain-specific
configuration files. See the
`Admin guide Identity Management Chapter
<https://docs.openstack.org/admin-guide/identity-domain-specific-config.html>`_
for more information.
