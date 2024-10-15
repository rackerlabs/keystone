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

import random
import secrets
import string

from oslo_config import fixture as config_fixture

from keystone.common import password_hashing
import keystone.conf
from keystone.tests import unit

CONF = keystone.conf.CONF


class TestPasswordHashing(unit.BaseTestCase):
    OPTIONAL = object()
    ITERATIONS: int = 10

    def setUp(self):
        super().setUp()
        self.config_fixture = self.useFixture(config_fixture.Config(CONF))

    def test_scrypt(self):
        self.config_fixture.config(strict_password_check=True)
        self.config_fixture.config(
            group="identity", password_hash_algorithm="scrypt"
        )
        self.config_fixture.config(group="identity", max_password_length="96")
        # Few iterations to test different inputs
        for _ in range(self.ITERATIONS):
            password: str = "".join(  # type: ignore
                secrets.choice(string.printable)
                for i in range(random.randint(1, 72))
            )
            hashed = password_hashing.hash_password(password)
            self.assertTrue(password_hashing.check_password(password, hashed))

    def test_bcrypt(self):
        self.config_fixture.config(strict_password_check=True)
        self.config_fixture.config(
            group="identity", password_hash_algorithm="bcrypt"
        )
        self.config_fixture.config(group="identity", max_password_length="72")
        # Few iterations to test different inputs
        for _ in range(self.ITERATIONS):
            password: str = "".join(  # type: ignore
                secrets.choice(string.printable)
                for i in range(random.randint(1, 72))
            )
            hashed = password_hashing.hash_password(password)
            self.assertTrue(password_hashing.check_password(password, hashed))

    def test_bcrypt_sha256(self):
        self.config_fixture.config(strict_password_check=True)
        self.config_fixture.config(
            group="identity", password_hash_algorithm="bcrypt_sha256"
        )
        self.config_fixture.config(group="identity", max_password_length="96")
        # Few iterations to test different inputs
        for _ in range(self.ITERATIONS):
            password: str = "".join(  # type: ignore
                secrets.choice(string.printable)
                for i in range(random.randint(1, 96))
            )
            hashed = password_hashing.hash_password(password)
            self.assertTrue(password_hashing.check_password(password, hashed))

    def test_pbkdf2_sha512(self):
        self.config_fixture.config(strict_password_check=True)
        self.config_fixture.config(
            group="identity", password_hash_algorithm="pbkdf2_sha512"
        )
        self.config_fixture.config(group="identity", max_password_length="96")
        # Do few iterations to process different inputs
        for _ in range(self.ITERATIONS):
            password: str = "".join(  # type: ignore
                secrets.choice(string.printable)
                for i in range(random.randint(1, 96))
            )
            hashed = password_hashing.hash_password(password)
            self.assertTrue(password_hashing.check_password(password, hashed))


class TestGeneratePartialPasswordHash(unit.BaseTestCase):
    def setUp(self):
        super().setUp()
        self.config_fixture = self.useFixture(config_fixture.Config(CONF))

    def test_equal_input_generates_equal_hash(self):
        h = password_hashing.generate_partial_password_hash

        kwargs1 = dict(
            password="password", salt="salt", secret_key="secret_key"
        )
        kwargs2 = dict(
            password="password", salt="salt", secret_key="secret_key"
        )

        hashed1 = h(**kwargs1)
        hashed2 = h(**kwargs2)

        self.assertEqual(hashed1, hashed2)

    def test_different_inputs_generate_different_hashes(self):
        h = password_hashing.generate_partial_password_hash

        params = [
            dict(
                msg="Different passwords",
                kwargs1=dict(
                    password="password1", salt="salt", secret_key="secret_key"
                ),
                kwargs2=dict(
                    password="password2", salt="salt", secret_key="secret_key"
                ),
            ),
            dict(
                msg="Different salts",
                kwargs1=dict(
                    password="password", salt="salt1", secret_key="secret_key"
                ),
                kwargs2=dict(
                    password="password", salt="salt2", secret_key="secret_key"
                ),
            ),
            dict(
                msg="Different secret_keys",
                kwargs1=dict(
                    password="password", salt="salt", secret_key="secret_key1"
                ),
                kwargs2=dict(
                    password="password", salt="salt", secret_key="secret_key2"
                ),
            ),
            dict(
                msg="Same but mixed inputs",
                kwargs1=dict(
                    password="secret_key", salt="password", secret_key="salt"
                ),
                kwargs2=dict(
                    password="salt", salt="secret_key", secret_key="password"
                ),
            ),
        ]

        for data in params:
            with self.subTest(msg=data["msg"]):
                hashed1 = h(**data["kwargs1"])
                hashed2 = h(**data["kwargs2"])
                self.assertNotEqual(hashed1, hashed2, msg=f"{data['msg']=}")

    def test_generates_partial_password_hash_by_default(self):
        h = password_hashing.generate_partial_password_hash

        # kwargs1 reads max_chars from CONF
        kwargs1 = dict(
            password="password", salt="salt", secret_key="secret_key"
        )
        kwargs2 = dict(
            password="password",
            salt="salt",
            secret_key="secret_key",
            max_chars=1000,
        )

        hashed1 = h(**kwargs1)
        hashed2 = h(**kwargs2)

        self.assertLess(len(hashed1), len(hashed2))

    def test_large_passwords(self):
        h = password_hashing.generate_partial_password_hash

        # 48042 bytes or 48 kB
        kwargs1 = dict(
            password="p" * 1000 * 48 + "1",
            salt="salt",
            secret_key="secret_key",
        )
        kwargs2 = dict(
            password="p" * 1000 * 48 + "2",
            salt="salt",
            secret_key="secret_key",
        )

        hashed1 = h(**kwargs1)
        hashed2 = h(**kwargs2)

        self.assertNotEqual(hashed1, hashed2)

    def test_different_conf_generates_different_hashes(self):
        h = password_hashing.generate_partial_password_hash

        args = ("password", "salt")

        params = [
            dict(
                msg="Different secret_keys",
                conf1=dict(
                    group="security_compliance",
                    invalid_password_hash_secret_key="secret_key1",
                ),
                conf2=dict(
                    group="security_compliance",
                    invalid_password_hash_secret_key="secret_key2",
                ),
            ),
            dict(
                msg="Different max chars",
                conf1=dict(
                    group="security_compliance",
                    invalid_password_hash_max_chars=3,
                ),
                conf2=dict(
                    group="security_compliance",
                    invalid_password_hash_max_chars=4,
                ),
            ),
            dict(
                msg="Different hash functions",
                conf1=dict(
                    group="security_compliance",
                    invalid_password_hash_function=("sha3_512"),
                ),
                conf2=dict(
                    group="security_compliance",
                    invalid_password_hash_function=("sha512"),
                ),
            ),
        ]

        for data in params:
            with self.subTest(msg=data["msg"]):
                self.config_fixture.config(**data["conf1"])
                hashed1 = h(*args)

                self.config_fixture.config(**data["conf2"])
                hashed2 = h(*args)

                self.assertNotEqual(hashed1, hashed2, msg=f"{data['msg']=}")

    def test_conf_secret_key_is_required(self):
        h = password_hashing.generate_partial_password_hash

        args = ("password", "salt")

        self.assertRaises(RuntimeError, h, *args)

    def test_returns_not_more_than_max_chars(self):
        h = password_hashing.generate_partial_password_hash

        kwargs = dict(
            password="password", salt="salt", secret_key="secret_key"
        )

        params = [1, 5, 1000]

        for max_chars in params:
            with self.subTest(msg=max_chars):
                hashed = h(**kwargs, max_chars=max_chars)

                self.assertLessEqual(
                    len(hashed), max_chars, msg=f"{max_chars=}"
                )

    def test_returns_full_password_hash(self):
        h = password_hashing.generate_partial_password_hash

        kwargs = dict(
            password="password", salt="salt", secret_key="secret_key"
        )

        # 1000 is larger than any supported hash function key length + base64
        # encoding
        hashed1 = h(**kwargs, max_chars=1000)

        params = [0, -1]

        for max_chars in params:
            with self.subTest(msg=max_chars):
                hashed2 = h(**kwargs, max_chars=max_chars)

                self.assertEqual(hashed1, hashed2)

    def test_invalid_function_raises_value_error(self):
        h = password_hashing.generate_partial_password_hash

        kwargs = dict(
            password="password",
            salt="salt",
            secret_key="secret_key",
            hash_function="invalid",
        )

        self.assertRaises(ValueError, h, **kwargs)
