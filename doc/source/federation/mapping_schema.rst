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

Mapping Schema
==============

-----------
Description
-----------

The schema for mapping is a description of how a mapping should be created.
It shows all the requirements and possibilities for a JSON to be used for mapping.

Mapping schema is validated with `JSON Schema
<http://json-schema.org/documentation.html>`__

--------------
Mapping Schema
--------------

The rules supported must use the following schema:

.. code-block:: javascript

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
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "user": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "email": {"type": "string"},
                                            "domain": {
                                                "$ref": "#/definitions/domain"
                                            },
                                            "type": {
                                                "type": "string",
                                                "enum": ["local",
                                                         "remote"]
                                            }
                                        },
                                        "additionalProperties": False
                                    },
                                    "group": {
                                        "type": "object",
                                        "oneOf": [
                                            {"$ref": "#/definitions/group_by_id"},
                                            {"$ref": "#/definitions/group_by_name"}
                                        ]
                                    },
                                    "groups": {
                                        "type": "string"
                                    },
                                    "group_ids": {
                                        "type": "string"
                                    },
                                    "domain": {"$ref": "#/definitions/domain"},
                                }
                            }
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
            },
            "domain": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                },
                "additionalProperties": False
            },
            "group_by_id": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"}
                },
                "additionalProperties": False,
                "required": ["id"]
            },
            "group_by_name": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "domain": {"$ref": "#/definitions/domain"}
                },
                "additionalProperties": False,
                "required": ["name", "domain"]
            }
        }
    }

.. NOTE::

    ``"additionalProperties": False``, shows that only the properties shown can be displayed.

    .. code-block:: javascript

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

    Keystone will not accept any other keys in the JSON mapping other than ``type``, and
    ``whitelist``.
