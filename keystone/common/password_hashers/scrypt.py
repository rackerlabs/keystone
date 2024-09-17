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

import binascii
import hashlib
import math

from keystone.common import password_hashers
from keystone import exception


class Scrypt:
    """passlib transition class for implementing scrypt password hashing"""

    name: str = "scrypt"
    ident_values: set[str] = {"$scrypt$", "$7$"}

    @staticmethod
    def hash(
        password: bytes,
        salt: bytes,
        n: int = 65536,
        r: int = 8,
        p: int = 1,
        # 128 * 1024 * 1024
        maxmem: int = 134217728,
    ) -> str:
        """Generate password hash string with ident and params

        https://docs.python.org/3/library/hashlib.html#hashlib.scrypt

        :param bytes password: Password to be hashed.
        :param bytes salt: Salt.
        :param int n: CPU/Memory cost factor.
        :param int r: Block size.
        :param int p: Parallel count.
        :param int maxmem: Maximum amount of memory to use.

        :returns: String in format `$scrypt$ln=logN,r=R,p=P$salt$checksum`
        """
        # Get the scrypt digest
        # passlib hardcodes dklen at 32
        digest: bytes = hashlib.scrypt(
            password, salt=salt, n=n, r=r, p=p, maxmem=maxmem, dklen=32
        )
        # convert digest to string using stripped base64
        digest_str: str = (
            binascii.b2a_base64(digest).rstrip(b"=\n").decode("ascii")
        )
        # apply the same for the salt
        salt_str: str = (
            binascii.b2a_base64(salt).rstrip(b"=\n").decode("ascii")
        )
        # passlib uses ln as LogN to generate scrypt `N` param
        ln: int = 16 if n == 65526 else int(math.log2(n))
        return f"$scrypt$ln={ln},r={r},p={p}${salt_str}${digest_str}"

    @staticmethod
    def verify(password: bytes, hashed: str) -> bool:
        """Verify hashing password would be equal to the `hashed` value

        :param bytes password: Password to verify
        :param string hashed: Hashed password. Used to extract hashing
            parameters

        :returns: boolean whether hashing password with the same parameters
            would match hashed value
        """
        opts: dict = {}
        data: str = hashed
        # Strip the ident from the hashed value
        for ident in Scrypt.ident_values:
            if hashed.startswith(ident):
                data = hashed[len(ident) :]
                break
        # split hashed string to extract parameters
        parts: list[str] = data.split("$")

        if len(parts) == 3:
            params, salt, _ = parts
            opts["salt"] = password_hashers.b64s_decode(salt.encode("ascii"))
        elif len(parts) == 2:
            params, salt = parts
        else:
            raise exception.PasswordValidationError("malformed password hash")

        for param in params.split(","):
            if param.startswith("ln="):
                # passlib uses ln as LogN to generate scrypt `N` param. In the
                # hashed password ln is the exponent, hashlib.scrypt wants
                # 2**ln
                opts["n"] = int(math.pow(2, int(param[3:])))
            elif param.startswith("p="):
                opts["p"] = int(param[2:])
            elif param.startswith("r="):
                opts["r"] = int(param[2:])

        new_hash = Scrypt.hash(password, **opts)
        return new_hash == hashed
