============================
Devstack plugin for Keystone
============================

This Devstack plugin automates the process of setting up a federated Keystone,
either as an Identity Provider or as a Service Provider (or both).

Setup
=====
Devstack loads its configuration from the `local.conf` file in the Devstack
root directory. To enable the plugin add the following line to the file:

.. code-block:: bash

    # local.conf
    enable_plugin keystone $KEYSTONE_REPO


Keystone-to-keystone Identity Provider
--------------------------------------
To set up Keystone as an Identity Provider enable the `k2k-idp` service by
adding the following line to `local.conf`:

.. code-block:: bash

    # local.conf
    # Enable the K2K Identity Provider service
    enable_service k2k-idp


After the setup is done, register the federated Keystone service providers
through the command line:

.. code-block:: bash

    openstack --os-identity-api-version 3 service provider create \
        --auth-url <SP_AUTH_URL> --service-provider-url <SP_URL> <SP_ID>


If using K2K federation, the `SP_AUTH_URL` and `SP_URL` values are as follows:

.. code-block:: bash

    SP_URL="http://<SP_IP>:5000/Shibboleth.sso/SAML2/ECP"
    SP_AUTH_URL="http://<SP_IP>:35357/v3/OS-FEDERATION/identity_providers/<IDP_ID>/protocols/saml2/auth"


It is also possible to have the plugin automate this step by providing the
``REGISTER_SP`` variable to ``local.conf``, alongside the ``SP_URL``,
``SP_AUTH_URL``, and ``SP_ID``. Automatically registering more than one
service provider is not currently supported.

Federation Service Provider
---------------------------
To setup Keystone as a Service Provider enable the ``federation-sp`` service
by adding the following lines to ``local.conf``:

.. code-block:: bash

    # local.conf
    # Enable the Federation Service Provider
    enable_service federation-sp


Then, set the following variables so that Devstack can configure Shibboleth
and register the Identity Provider (sample values provided for K2K):

.. code-block:: bash

    REGISTER_IDP=true
    IDP_REMOTE_ID=http://<IDP_IP>:35357/v3/OS-FEDERATION/saml2/idp
    IDP_METADATA=http://<IDP_IP>:5000/v3/OS-FEDERATION/saml2/metadata
    IDP_ID=idp
    FEDERATION_PROTOCOL=saml2
    FEDERATION_MAPPING=k2k


If the ``REGISTER_IDP`` variable is not set, the plugin will not perform the
registration step.

The ``FEDERATION_MAPPING`` variable accepts the path to a user-provided
mapping file instead of the k2k mapping.

Be aware that the configuration provided for Apache is not safe to use in
production environments as it doesn't validate whether the identity provider
is registered in Keystone. More information available `here
<http://lists.openstack.org/pipermail/openstack-dev/2015-April/061919.html>`_.

Testing
=======
Generic Federation
------------------
For testing generic federation, one Identity Provider must have been
previously setup.

Keystone-to-Keystone
--------------------
For testing K2K, one Devstack can be set up as the Identity Provider and
another one as the Service Provider. K2K-specific Tempest tests can then be
run on the Identity Provider. Alternatively, a single Devstack can also
perform both functions.
