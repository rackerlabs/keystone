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

Supported Mapping Rules
-----------------------

Mappings support 4 different types of rules:

``empty``: TODO
``any_one_of``: TODO
``not_any_of``: TODO
``blacklist``: TODO
``whitelist``: TODO

You can combine multiple rules in a single mapping.

The rules supported must use the following schema:

.. code-block:: json

    {
        "type": "object",
        "required": ['rules'],
        "properties": {
            "rules": {
                "minItems": 1,
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ['local', 'remote'],
                    "additionalProperties": False,
                    "properties": {
                        "local": {
                            "type": "array"
                        },
                        "remote": {
                            "minItems": 1,
                            "type": "array",
                            "items": {
                                "type": "object",
                                "oneOf": [
                                    {"$ref": "#/definitions/empty"},
                                    {"$ref": "#/definitions/any_one_of"},
                                    {"$ref": "#/definitions/not_any_of"},
                                    {"$ref": "#/definitions/blacklist"},
                                    {"$ref": "#/definitions/whitelist"}
                                ],
                            }
                        }
                    }
                }
            }
        },
        "definitions": {
            "empty": {
                "type": "object",
                "required": ['type'],
                "properties": {
                    "type": {
                        "type": "string"
                    },
                },
                "additionalProperties": False,
            },
            "any_one_of": {
                "type": "object",
                "additionalProperties": False,
                "required": ['type', 'any_one_of'],
                "properties": {
                    "type": {
                        "type": "string"
                    },
                    "any_one_of": {
                        "type": "array"
                    },
                    "regex": {
                        "type": "boolean"
                    }
                }
            },
            "not_any_of": {
                "type": "object",
                "additionalProperties": False,
                "required": ['type', 'not_any_of'],
                "properties": {
                    "type": {
                        "type": "string"
                    },
                    "not_any_of": {
                        "type": "array"
                    },
                    "regex": {
                        "type": "boolean"
                    }
                }
            },
            "blacklist": {
                "type": "object",
                "additionalProperties": False,
                "required": ['type', 'blacklist'],
                "properties": {
                    "type": {
                        "type": "string"
                    },
                    "blacklist": {
                        "type": "array"
                    }
                }
            },
            "whitelist": {
                "type": "object",
                "additionalProperties": False,
                "required": ['type', 'whitelist'],
                "properties": {
                    "type": {
                        "type": "string"
                    },
                    "whitelist": {
                        "type": "array"
                    }
                }
            }
        }
    }

Supported Mappings Examples
---------------------------

The following are all examples of supported mapping rule types.

empty:
~~~~~~

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
                        "type": "HTTP_OIDC_GROUPIDS"
                    }
                ]
            }
        ]
    }

any_one_of:
~~~~~~~~~~~

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
                        "type": "HTTP_OIDC_GROUPIDS",
                        "any_one_of": [
                            "HTTP_OIDC_EMAIL"
                        ]
                    }
                ]
            }
        ]
    }


not_any_of:
~~~~~~~~~~~

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
                        "type": "HTTP_OIDC_GROUPIDS",
                        "not_any_of": [
                            "HTTP_OIDC_EMAIL"
                        ]
                    }
                ]
            }
        ]
    }

blacklist:
~~~~~~~~~~

.. code-block:: json

    {
        "rules": [
            {
                "remote": [
                    {
                        "type": "HTTP_OIDC_GROUPIDS",
                        "blacklist": [
                            "HTTP_OIDC_EMAIL"
                        ]
                    },
                    {
                        "type": "UserName"
                    }
                ],
                "local": [
                    {
                        "groups": "{0}",
                        "domain": {
                            "id": "0cd5e9"
                        }
                    },
                    {
                        "user": {
                            "name": "{1}"
                        }
                    }
                ]
            }
        ]
    }

whitelist:
~~~~~~~~~~

.. code-block:: json

    {
        "rules": [
            {
                "remote": [
                    {
                        "type": "HTTP_OIDC_GROUPIDS",
                        "whitelist": [
                            "HTTP_OIDC_EMAIL"
                        ]
                    },
                    {
                        "type": "UserName"
                    }
                ],
                "local": [
                    {
                        "groups": "{0}",
                        "domain": {
                            "id": "0cd5e9"
                        }
                    },
                    {
                        "user": {
                            "name": "{1}"
                        }
                    }
                ]
            }
        ]
    }
