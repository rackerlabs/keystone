# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import unittest

from keystone.auth import schema
from keystone.common import validation
from keystone import exception


class TestValidatePost(unittest.TestCase):
    def _expect_failure(self, post_data):
        with self.assertRaises(exception.SchemaValidationError):
            validation.lazy_validate(schema.token_issue, post_data)

    def test_auth_not_object_ex(self):
        self._expect_failure('something')

    def test_auth_no_identity_ex(self):
        self._expect_failure({})

    def test_identity_not_object_ex(self):
        self._expect_failure({'identity': 'something'})

    def test_no_methods_ex(self):
        self._expect_failure({'identity': {}})

    def test_methods_not_array_ex(self):
        p = {'identity': {'methods': 'something'}}
        self._expect_failure(p)

    def test_methods_not_array_str_ex(self):
        p = {'identity': {'methods': [{}]}}
        self._expect_failure(p)

    def test_no_password(self):
        # password may not be present.
        post_data = {
            'identity': {
                'methods': ['password'],
            },
        }
        validation.lazy_validate(schema.token_issue, post_data)

    def test_password_not_object(self):
        # if password is present, it must be an object.
        p = {
            'identity': {
                'methods': ['password'],
                'password': 'something',
            },
        }
        self._expect_failure(p)

    def test_user_not_object(self):
        # if user is present, it must be an object
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': 'something',
                },
            },
        }
        self._expect_failure(p)

    def test_user_name_not_string(self):
        # if user name is present, it must be a string
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'name': 1,
                    },
                },
            },
        }
        self._expect_failure(p)

    def test_user_id_not_string(self):
        # if user id is present, it must be a string
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'id': {},
                    },
                },
            },
        }
        self._expect_failure(p)

    def test_user_password_not_string(self):
        # if user password is present, it must be a string
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'password': {},
                    },
                },
            },
        }
        self._expect_failure(p)

    def test_user_domain_not_object(self):
        # if user domain is present, it must be an object
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'domain': 'something',
                    },
                },
            },
        }
        self._expect_failure(p)

    def test_user_domain_name_not_string(self):
        # if user domain name is present, it must be a string.
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'domain': {
                            'name': {}
                        },
                    },
                },
            },
        }
        self._expect_failure(p)

    def test_user_domain_id_not_string(self):
        # if user domain id is present, it must be a string.
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'domain': {
                            'id': {}
                        },
                    },
                },
            },
        }
        self._expect_failure(p)

    def test_scope_not_object_or_string_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': 1,
        }
        self._expect_failure(p)

    def test_project_not_object_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'project': 'something',
            },
        }
        self._expect_failure(p)

    def test_project_name_not_string_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'project': {
                    'name': {},
                },
            },
        }
        self._expect_failure(p)

    def test_project_id_not_string_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'project': {
                    'id': {},
                },
            },
        }
        self._expect_failure(p)

    def test_project_domain_not_object_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'project': {
                    'domain': 'something',
                },
            },
        }
        self._expect_failure(p)

    def test_project_domain_name_not_string_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'project': {
                    'domain': {'name': {}, },
                },
            },
        }
        self._expect_failure(p)

    def test_project_domain_id_not_string_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'project': {
                    'domain': {'id': {}, },
                },
            },
        }
        self._expect_failure(p)

    def test_domain_not_object_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'domain': 'something',
            },
        }
        self._expect_failure(p)

    def test_domain_id_not_string_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'domain': {'id': {}, },
            },
        }
        self._expect_failure(p)

    def test_domain_name_not_string_ex(self):
        p = {
            'identity': {'methods': [], },
            'scope': {
                'domain': {'name': {}, },
            },
        }
        self._expect_failure(p)

    def test_unscoped(self):
        post_data = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'name': 'admin',
                        'domain': {
                            'name': 'Default',
                        },
                        'password': 'devstacker',
                    },
                },
            },
        }
        validation.lazy_validate(schema.token_issue, post_data)

    def test_user_domain_id(self):
        post_data = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'name': 'admin',
                        'domain': {
                            'id': 'default',
                        },
                        'password': 'devstacker',
                    },
                },
            },
        }
        validation.lazy_validate(schema.token_issue, post_data)

    def test_two_methods(self):
        post_data = {
            'identity': {
                'methods': ['password', 'mapped'],
                'password': {
                    'user': {
                        'name': 'admin',
                        'domain': {
                            'name': 'Default',
                        },
                        'password': 'devstacker',
                    },
                },
            },
        }
        validation.lazy_validate(schema.token_issue, post_data)

    def test_project_scoped(self):
        post_data = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'name': 'admin',
                        'domain': {
                            'name': 'Default',
                        },
                        'password': 'devstacker',
                    },
                },
            },
            'scope': {
                'project': {
                    'name': 'demo',
                    'domain': {
                        'name': 'Default',
                    },
                },
            },
        }
        validation.lazy_validate(schema.token_issue, post_data)

    def test_domain_scoped(self):
        post_data = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'name': 'admin',
                        'domain': {
                            'name': 'Default',
                        },
                        'password': 'devstacker',
                    },
                },
            },
            'scope': {
                'domain': {
                    'name': 'Default',
                },
            },
        }
        validation.lazy_validate(schema.token_issue, post_data)

    def test_explicit_unscoped(self):
        post_data = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'name': 'admin',
                        'domain': {
                            'name': 'Default',
                        },
                        'password': 'devstacker',
                    },
                },
            },
            'scope': 'unscoped',
        }
        validation.lazy_validate(schema.token_issue, post_data)

    def test_extra_properties(self):
        # Everything can have extra fields and they're ignored.
        p = {
            'identity': {
                'methods': ['password'],
                'password': {
                    'user': {
                        'extra4': 'whatever4',
                        'domain': {'extra5': 'whatever5', }
                    },
                    'extra3': 'whatever3',
                },
                'extra4': 'whatever4',
            },
            'scope': {
                'project': {
                    'domain': {'extra8': 'whatever8', },
                    'extra7': 'whatever7',
                },
                'domain': {
                    'extra9': 'whatever9',
                },
                'extra6': 'whatever6',
            },
            'extra2': 'whatever2',
        }
        validation.lazy_validate(schema.token_issue, p)
