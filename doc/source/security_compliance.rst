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

=============================
Security Compliance & PCI-DSS
=============================

As of the Newton release, keystone added new features around security
compliance, specifically to satisfy Payment Card Industry - Data Security
Standard (PCI-DSS) v3.1 requirements.  However, these features could be used to
satisfy other security requirements as well.  See `Security Hardening: PCI-DSS
<https://github.com/openstack/keystone-specs/blob/master/specs/keystone/newton/
pci-dss.rst#security-hardening-pci-dss>`_ for more information on PCI-DSS.

These features can be enabled by changing the configuration settings under the
``[security_compliance]`` section in keystone.conf

.. NOTE::

    Most of these features only apply to the SQL backend for the identity
    driver.

Disabling Inactive Users
------------------------

PCI-DSS 8.1.4 requires that inactive user accounts be removed or disabled
within 90 days.  You can achieve this by setting the
``disable_user_account_days_inactive``:

.. code-block:: ini

    [security_compliance]
    disable_user_account_days_inactive = 90

This setting means, that users that have not authenticated (inactive) for the
past 90 days will be automatically disabled.  Users can be re-enabled by
explicitly setting the enable user attribute via the API.

Account Lockout Threshold
-------------------------

The account lockout feature limits the number of times a user can attempt to
login with an incorrect password.  First, you can set the maximum number of
failed authentication attempts by setting the ``lockout_failure_attempts``:

.. code-block:: ini

    [security_compliance]
    lockout_failure_attempts = 6

You can then set the number of minutes a user would be locked out by setting
the ``lockout_duration`` in seconds:

.. code-block:: ini

    [security_compliance]
    lockout_duration = 1800

If the ``lockout_duration`` is not set, then users may be locked out
indefinitely until the user is explicitly enabled via the API.

Password Strength Requirements
------------------------------

Password History Requirements
------------------------------
