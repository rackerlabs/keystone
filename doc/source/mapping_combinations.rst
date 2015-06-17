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

Description
-----------

The mapping engine can be tested before creating a federated setup.
It can be tested with the keystone-manage command:

keystone-manage --mapping_engine --rules <file> --input <file>

--rules will be the path to the file with the rules which will be
executed. The file must be a proper JSON structure with the top-level
key 'rules' and all corresponding values being a list.

--input will be the path to a file containing the input attributes.

For the rest of this doc, we can assume --input is:
``HTTP_OIDC_EMAIL``: me@example.com
``HTTP_OIDC_GROUPIDS``: cn=IBM_Canada_Lab;cn=IBM_USA_Lab

Supported Mappings and Output
-----------------------------

Small Mapping:
~~~~~~~~~~~~~~
.. code-block:: json

    {
        "rules": [
            {
                "local": [
                    {
                        "group": {
                            "id": "0cd5e9"
                        }
                    },
                    {
                        "user": {
                            "name": "{0}"
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
                    },
                    {
                        "type": "LastName",
                        "any_one_of": [
                            "Bo"
                        ]
                    }
                ]
            },
            {
                "local": [
                    {
                        "group": {
                            "id": "85a868"
                        }
                    },
                    {
                        "user": {
                            "name": "{0}"
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
                    },
                    {
                        "type": "FirstName",
                        "any_one_of": [
                            "Jill"
                        ]
                    }
                ]
            }
        ]
    }

Output:

.. code-block:: json

    {
      "group_ids": [],
      "user": {
        "domain": {
          "id": "Federated"
        },
        "type": "ephemeral"
      },
      "group_names": []
    }

Large Mapping:
~~~~~~~~~~~~~~
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
                            "id": "0cd5e9"
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
                        "type": "orgPersonType",
                        "any_one_of": [
                            "Admin",
                            "Big Cheese"
                        ]
                    }
                ]
            },
            {
                "local": [
                    {
                        "user": {
                            "name": "{0}",
                            "email": "{1}"
                        }
                    }
                ],
                "remote": [
                    {
                        "type": "UserName"
                    },
                    {
                        "type": "Email"
                    },
                    {
                        "type": "orgPersonType",
                        "not_any_of": [
                            "Admin",
                            "Employee",
                            "Contractor",
                            "Tester"
                        ]
                    }
                ]
            },
            {
                "local": [
                    {
                        "group": {
                            "id": "123"
                        }
                    },
                    {
                        "group": {
                            "id": "xyz"
                        }
                    },
                    {
                        "user": {
                            "name": "{0}"
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
                            "Tester"
                        ]
                    },
                    {
                        "type": "Email",
                        "any_one_of": [
                            ".*@example.com$"
                        ]
                    }
                ]
            }
        ]
    }

Output:

.. code-block:: json

    {
      "group_ids": [],
      "user": {
        "domain": {
          "id": "Federated"
        },
        "type": "ephemeral"
      },
      "group_names": []
    }

