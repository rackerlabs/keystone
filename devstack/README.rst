============================
DevStack plugin for Keystone
============================

This DevStack plugin automates the process of setting up a federated Keystone,
either as an Identity Provider or as a Service Provider. These functions can
either be enabled on the same DevStack or on separate ones depending on use
case.

Setup
=====
DevStack loads its configuration from the `local.conf` file in the DevStack
root directory. To enable the plugin add the following line to the file:

.. code-block:: bash

    # local.conf
    enable_plugin keystone $KEYSTONE_REPO


K2K Identity Provider
---------------------
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


Federation Service Provider
---------------------------
To setup Keystone as a Service Provider enable the `federation-sp` service by
adding the following lines to `local.conf`:

.. code-block:: bash

    # local.conf
    # Enable the Federation Service Provider
    enable_service federation-sp


Then, set the following variables so that DevStack can configure shibboleth
and register the Identity Provider (sample values provided for K2K):

.. code-block:: bash

    IDP_REMOTE_ID=http://<IDP_IP>:35357/v3/OS-FEDERATION/saml2/idp
    IDP_METADATA=http://<IDP_IP>:5000/v3/OS-FEDERATION/saml2/metadata
    IDP_ID=idp
    FEDERATION_PROTOCOL=saml2
    FEDERATION_MAPPING=k2k


Testing
=======
Keystone 2 Keystone
-------------------
For testing K2K, one DevStack can be set up as the Identity Provider and
another one as the Service Provider. K2K-specific Tempest tests can then be
run on the Identity Provider.

Alternatively, one DevStack can also perform both functions.
