# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Fixtures for Federation Mapping."""

MAPPING_SMALL = {
    'name': 'large mapping',
    "rules": [
        {
            "local": [
                {
                    "group": {
                        "id": "0cd5e9"
                    }
                }
            ],
            "remote": [
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
                        "Smith"
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
                }
            ],
            "remote": [
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

MAPPING_LARGE = {
    'name': 'new mapping',
    "rules": [
        {
            "local": [
                {
                    "user": {
                        "name": "$0 $1",
                        "email": "$2"
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
                        "name": "$0",
                        "email": "$1"
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
                    "any_one_of": [
                        "Customer"
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
                }
            ],
            "remote": [
                {
                    "type": "orgPersonType",
                    "any_one_of": [
                        "Tester"
                    ]
                },
                {
                    "type": "Email",
                    "any_one_of": [
                        "^@example.com$"
                    ],
                    "regex": True
                }
            ]
        }
    ]
}


MAPPING_BAD_REQ = {
    'name': 'bad requirement mapping',
    "rules": [
        {
            "local": [
                {
                    "user": "name"
                }
            ],
            "remote": [
                {
                    "type": "UserName",
                    "bad_requirement": [
                        "Young"
                    ]
                }
            ]
        }
    ]
}

MAPPING_BAD_VALUE = {
    'name': 'bad requirement mapping',
    "rules": [
        {
            "local": [
                {
                    "user": "name"
                }
            ],
            "remote": [
                {
                    "type": "UserName",
                    "any_one_of": "should_be_list"
                }
            ]
        }
    ]
}

MAPPING_NO_RULES = {
    'name': 'no rules',
    'rules': []}

MAPPING_NO_REMOTE = {
    'name': 'bad requirement mapping',
    "rules": [
        {
            "local": [
                {
                    "user": "name"
                }
            ],
            "remote": []
        }
    ]
}

MAPPING_MISSING_LOCAL = {
    'name': 'bad requirement mapping',
    "rules": [
        {
            "remote": [
                {
                    "type": "UserName",
                    "any_one_of": "should_be_list"
                }
            ]
        }
    ]
}

ASSERTION_ADMIN = {
    'Email': 'admin@admin.com',
    'UserName': 'jsmith',
    'FirstName': 'Joe',
    'LastName': 'Smith',
    'orgPersonType': 'Domain Users;Admin;;'
}

ASSERTION_CUSTOMER = {
    'Email': 'customer@customer.domain.com',
    'UserName': 'smithj',
    'FirstName': 'Jill',
    'LastName': 'Smith',
    'orgPersonType': 'Contractor;SubContractor;Customer;;'
}
