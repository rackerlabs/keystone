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
Mapping Combinations for Federation
===================================

-----------
Description
-----------

Mapping adds a set of rules to map federation protocol attributes to Identity API objects.
An Identity Provider has exactly one mapping specified per protocol.

Mapping objects can be used multiple times by different combinations of Identity Provider and Protocol.

-----------
Definitions
-----------

A mapping hierarchy looks as follows:

.. code-block:: json

    {
        "mapping": {
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
    }


* `mapping`: top-level of a mapping.
* `rules`: top-level of a set of rules.
* `local`: a rule containing information on what local attributes will be mapped.
* `remote`: a rule containing information on what remote attributes will be mapped.
* `<condition>`: contains information on conditions that allow a rule, can only
  be set in a `remote` rule.

---------------
Supported Rules
---------------

Mapping Engine
--------------

The mapping engine can be tested before creating a federated setup.
It can be tested with the keystone-manage command:

.. code-block:: bash

    $ keystone-manage --mapping_engine --rules <file> --input <file>

--rules will be the path to the file with the rules which will be
executed. The file must be a proper JSON structure with the top-level
key 'rules' and all corresponding values being a list.

--input will be the path to a file containing the input attributes.

.. NOTE::

    Here is an example of a file that --input can use:

    ::

        ``HTTP_OIDC_EMAIL``: me@example.com
        ``HTTP_OIDC_GROUPIDS``: cn=IBM_Canada_Lab;cn=IBM_USA_Lab

Supported Mapping Conditions
----------------------------

Mappings support 5 different types of conditions:

``empty``: The rule is matched to all claims containing the remote attribute type.
This condition does not need to be specified. Example is shown below.

``any_one_of``: The rule is matched only if any of the specified strings appear
in the remote attribute type.

``not_any_of``: The rule is not matched if any of the specified strings appear
in the remote attribute type.

``blacklist``: The rule allows all except specified set of groups

``whitelist``: The rules allows specified set of groups

You can combine multiple rules in a single mapping.
The schema that needs to be followed for the mapping rules can be seen
in the :doc:`mapping_schema` page.

Supported Mappings Examples
---------------------------

The following are all examples of supported mapping rule types.

empty condition:
~~~~~~~~~~~~~~~~

.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "user": {
                            "name": "{0} {1}",
                            "email": "{2}"
                        },
                        "group": {
                            "name": "{3}"
                        }
                    }
                ],
                "remote": [
                    {
                        "type": "FirstName"
                    },
                    {
                        "type": "LastName"
                    },
                    {
                        "type": "Email"
                    },
                    {
                        "type": "OIDC_GROUPS"
                    }
                ]
            }
        ]
    }

.. NOTE::

    The numbers in {} are are indices. They map in order. For Example:

    ::

        Mapping to user with the name matching the value in remote attribute OS_FIRST_NAME
        Mapping to user with the name matching the value in remote attribute OS_LAST_NAME
        Mapping to user with the email matching value in remote attribute OS_EMAIL
        Mapping to a group(s) with the name matching the value(s) in remote attribute OIDC_GROUPS

    Groups can have multiple values.
    Example: OIDC_GROUPS=developers;testers


other conditions:
~~~~~~~~~~~~~~~~~

In ``<other_condition>`` please supply one of the following:
``any_one_of``, ``not_any_of``, ``blacklist``, or ``whitelist``.

.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        },
                        "group": {
                            "id": "0cd5e9"
                        }
                    }
                ],
                "remote": [
                    {
                    "type": "UserName"
                    },
                    {
                        "type": "HTTP_OIDC_GROUPIDS",
                        "<other_condition>": [
                            "HTTP_OIDC_EMAIL"
                        ]
                    }
                ]
            }
        ]
    }

.. NOTE::

    If the user attribute is missing when processing an assertion, the server tries to
    directly map REMOTE_USER environment variable. If this variable is also unavailable
    the server returns an HTTP 401 Unauthorized error.

Group Names can also be provided in the local section:

.. code-block:: json

    "local": [
        {
            "group": {
                "name": "developer_group",
                "domain": {
                    "id": "abc1234"
                }
            }
        }
    ]

.. code-block:: json

    "local": [
        {
            "group": {
                "name": "developer_group",
                "domain": {
                    "name": "private_cloud"
                }
            }
        }
    ]


Output:
-------

If a mapping is valid you will receive the following output.

.. code-block:: json

    {
      "group_ids": [<group_ids>],
      "user": {
        "domain": {
          "id": "Federated" or "<local>"
        },
        "type": "ephemeral" or "<local>",
        "name": "<local>",
        "id": "<local>"
      },
      "group_names": [<group_names>]
    }

``<local>``: If the user has domain specified, the user is treated as existing in the backend,
hence the server will fetch user details (id, name, roles, groups). ``<local>`` will be replaced
by the user's information.

``Federated``: If no domain is specified in the local rule,
user is deemed ephemeral and becomes a member of service domain named Federated.

``ephemeral``: A user that does not exist in the backend.

.. NOTE::

    group_ids and/or group_names will only be displayed if they were set in the rules under local, otherwise
    they will be empty.

Regular Expressions:
--------------------

Regular Expressions can be used in a mapping.

.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        },
                        "group": {
                            "id": "0cd5e9"
                        }
                    },
                ],
                "remote": [
                    {
                    "type": "UserName"
                    },
                    {
                        "type": "cn=IBM_USA_Lab",
                        "any_one_of": [
                            ".*@yeah.com$"
                        ]
                        "regex": true
                    }
                ]
            }
        ]
    }

This allows any user with the following claim information to be mapped to
group with id 0cd5e9.

.. code-block:: json

    {"cn=IBM_USA_Lab":"<any_name>@yeah.com"}


Condition Combinations:
-----------------------

Combinations of the Supported Mappings can also be done.

``empty``, ``any_one_of``, and ``not_any_of`` can all be used in the same mapping.
``any_one_of`` and ``not_any_of`` are mutually exclusive. ``whitelist`` and ``blacklist`` cannot be used together.

.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        },
                        "group": {
                            "id": "0cd5e9"
                        }
                    },
                ],
                "remote": [
                    {
                    "type": "UserName"
                    },
                    {
                        "type": "cn=IBM_Canada_Lab",
                        "not_any_of": [
                            ".*@naww.com$"
                        ],
                        "regex": true
                    },
                    {
                        "type": "cn=IBM_USA_Lab",
                        "any_one_of": [
                            ".*@yeah.com$"
                        ]
                        "regex": true
                    }
                ]
            }
        ]
    }

As before group names and users can also be provided in the local section.

This allows any user with the following claim information to be mapped to
group with id 0cd5e9.

.. code-block:: json

     {"Email":"<any_name>@yeah.com"}
     {"cn=IBM_USA_Lab":"<any_name>@yeah.com"}
     {"cn=IBM_Canada_Lab":"<any_name>@yeah.com"}

::

    any claim containing the key Email.
    any claim containing key cn=IBM_Canada_Lab that doesn't have the value <any_name>@naww.com.
    any claim containing key cn=IBM_USA_Lab that has value <any_name>@yeah.com.

Multiple Rules:
---------------

Multiple rules can also be utilized in a mapping.

.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        },
                        "group": {
                            "name": "non-contractors",
                            "domain": {
                                "id": "abc1234"
                            }
                        }
                    }
                ],
                "remote": [
                    {
                    "type": "UserName"
                    },
                    {
                        "type": "orgPersonType",
                        "not_any_of": [
                            "Contractor",
                            "SubContractor"
                        ]
                    }
                ]
            },
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}"
                        },
                        "group": {
                            "name": "contractors",
                            "domain": {
                                "id": "abc1234"
                            }
                        }
                    }
                ],
                "remote": [
                    {
                    "type": "UserName"
                    },
                    {
                        "type": "orgPersonType",
                        "any_one_of": [
                            "Contractor",
                            "SubContractor"
                        ]
                    }
                ]
            }
        ]
    }

The above shows that all orgPersonType:
::

    that are not Contractor or SubContractor will belong to the non-contractors group.
    that are Contractor or Subcontractor will belong to the contractors group.

