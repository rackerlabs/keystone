from keystone import exception
from keystone.federation import utils
from keystone.tests import unit

good_mapping = {
    "rules": [
        {
            "local": [
                {
                    "user": {
                        "name": "{0}",
                        "domain": {"id": "default"},
                        "type": "local"
                    }
                }
            ],
            "remote": [
                {
                    "type": "UserName"
                }
            ]
        }
    ]
}

bad_mapping = {
    "rules": [
        {
            "local": [
                {
                    "user": {
                        "name": "{0}",
                        "domain": {"id": "default"}
                    },
                    "type": "local"
                }
            ],
            "remote": [
                {
                    "type": "UserName"
                }
            ]
        }
    ]
}


class ValidationTests(unit.BaseTestCase):

    def test_good_local(self):
        try:
            utils.validate_mapping_structure(good_mapping)
        except exception.ValidationError:
            self.fail()

    def test_bad_local(self):
        self.assertRaises(exception.ValidationError,
                          utils.validate_mapping_structure,
                          bad_mapping)
