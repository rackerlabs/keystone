.. _multi_factor_authentication:

===========================
Multi-Factor Authentication
===========================

Configuring MFA
===============

MFA is configured on a per user basis via the user options
:ref:`multi_factor_auth_rules` and :ref:`multi_factor_auth_enabled`. Until
these are set the user can authenticate with any one of the enabled auth
methods.

MFA rules
---------

The MFA rules allow an admin to force a user to use specific forms of
authentication or combinations of forms of authentication to get a token.

The rules are specified as follows via the user option
:ref:`multi_factor_auth_rules`::

    [["password", "totp"], ["password", "custom-auth-method"]]

They are a list of lists. The elements of the sub-lists must be strings and are
intended to mirror the required authentication method names (e.g. ``password``,
``totp``, etc) as defined in the ``keystone.conf`` file in the
``[auth] methods`` option. Each list of methods specifies a rule.

If the auth methods provided by a user match (or exceed) the auth methods in
the list, that rule is used. The first rule found (rules will not be processed
in a specific order) that matches will be used. If a user has the ruleset
defined as ``[["password", "totp"]]`` the user must provide both password and
totp auth methods (and both methods must succeed) to receive a token. However,
if a user has a ruleset defined as ``[["password"], ["password", "totp"]]``
the user may use the ``password`` method on it's own but would be required
to use both ``password`` and ``totp`` if ``totp`` is specified at all.

Any auth methods that are not defined in ``keystone.conf`` in the
``[auth] methods`` option are ignored when the rules are processed. Empty
rules are not allowed. If a rule is empty due to no-valid auth methods
existing within it, the rule is discarded at authentication time. If there
are no rules or no valid rules for the user, authentication occurs in the
default manner: any single configured auth method is sufficient to receive
a token.

.. note::

    The ``token`` auth method typically should not be specified in any MFA
    Rules. The ``token`` auth method will include all previous auth methods
    for the original auth request and will match the appropriate ruleset. This
    is intentional, as the ``token`` method is used for rescoping/changing
    active projects.

Enabling MFA
------------

Before the MFA rules take effect on a user, MFA has to be enabled for that user
via the user option :ref:`multi_factor_auth_enabled`. By default this is unset,
and the rules will not take effect until configured.

In the case a user should be exempt from MFA Rules, regardless if they are
set, the User-Option may be set to ``False``.

Using MFA
---------

Multi-Factor Authentication with Keystone can be used in two ways, either you
treat it like current single method authentication and provide all the details
upfront, or you doing it as a multi-step process with auth receipts.

Single step
+++++++++++

In the single step approach you would supply all the required authentication
methods in your request for a token:

.. code-block:: json

    { "auth": {
            "identity": {
                "methods": [
                    "password",
                    "totp"
                ],
                "totp": {
                    "user": {
                        "id": "2ed179c6af12496cafa1d279cb51a78f",
                        "passcode": "012345"
                    }
                },
                "password": {
                    "user": {
                        "id": "2ed179c6af12496cafa1d279cb51a78f",
                        "password": "super sekret pa55word"
                    }
                }
            }
        }
    }

If all the supplied auth methods are valid, Keystone will return a token.

Multi-Step
++++++++++

In the multi-step approach you can supply any one method from the auth rules:

.. code-block:: json

    { "auth": {
            "identity": {
                "methods": [
                    "password"
                ],
                "password": {
                    "user": {
                        "id": "2ed179c6af12496cafa1d279cb51a78f",
                        "password": "super sekret pa55word"
                    }
                }
            }
        }
    }

Provided the method is valid, Keystone will still return a ``401``, but will in
the response header ``Openstack-Auth-Receipt`` return a receipt of valid auth
method for reuse later.

The response body will also contain information about the auth receipt, and
what auth methods may be missing:

.. code-block:: json

    {
        "receipt":{
            "expires_at":"2018-07-05T08:39:23.000000Z",
            "issued_at":"2018-07-05T08:34:23.000000Z",
            "methods": [
                "password"
            ],
            "user": {
                "domain": {
                    "id": "default",
                    "name": "Default"
                },
                "id": "ee4dfb6e5540447cb3741905149d9b6e",
                "name": "admin"
            }
        },
        "required_auth_methods": [
            ["totp", "password"]
        ]
    }

Now you can continue authenticating by supplying the missing auth methods, and
supplying the header ``Openstack-Auth-Receipt`` as gotten from the previous
response:

.. code-block:: json

    { "auth": {
            "identity": {
                "methods": [
                    "totp"
                ],
                "totp": {
                    "user": {
                        "id": "2ed179c6af12496cafa1d279cb51a78f",
                        "passcode": "012345"
                    }
                }
            }
        }
    }

Provided the auth methods are valid, Keystone will now supply a token. If not
you can try again until the auth receipt expires (e.g in case of TOTP timeout).

Supported multi-factor authentication methods
=============================================

TOTP is the only suggested second factor along with password for now, but there
are plans to include more in future.

TOTP
----

This is a simple 6 digit passcode generated by both the server and client from
a known shared secret.

This used in a multi-step fashion is the most common 2-factor method used these
days.

See: :ref:`auth_totp`
