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
#

"""Supports for jwt_token authorization method """


from oslo_log import log
import six
import jwt
import flask

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from keystone.auth.plugins import base
from keystone.auth.plugins import mapped
from keystone.common import provider_api
from keystone import exception

import keystone.conf

LOG = log.getLogger(__name__)

CONF = keystone.conf.CONF.jwt_token
PROVIDERS = provider_api.ProviderAPIs
MODULE_NAME='jwt_token'


class JWTToken(base.AuthMethodHandler):

    def __init__(self):
        self._public_key = None

    def authenticate(self, auth_payload):
        """
          Performs authentication process using JWT token supplied in 'Authorization' header
          Firstly check if header is valid - that means, if is in format 'Authorization: Bearer XXXX'
          Then parses JWT token in header and verify it agains - expiration time, issuer and check signature - according to configuration.
          If everything is ok, payload from token is extracted and then passed to maping engine.
        """

        authorization_header_value = flask.request.headers.get('Authorization')
        if not authorization_header_value:
            raise exception.ValidationError(attribute='Authorization', target='request.headers')

        authorization_header_arr = authorization_header_value.split(' ')
        if len(authorization_header_arr) != 2:
            raise exception.Unauthorized('Invalid authorization header value')

        if authorization_header_arr[0] != 'Bearer':
            raise exception.Unauthorized('Invalid authorization header value')


        jwt_header = None
        jwt_payload = None

        try:
          jwt_header = jwt.get_unverified_header(authorization_header_arr[1])

          if not 'alg' in jwt_header:
            raise jwt.exceptions.InvalidAlgorithmError('No algorithm specified')

          if not jwt_header['alg'] in self._get_valid_algorithms():
            raise jwt.exceptions.InvalidAlgorithmError('Unsupported algorithm given')

          if jwt_header['alg'].startswith('RS'):
            jwt_payload = jwt.decode(authorization_header_arr[1],
              key=self._load_public_key(),
              algorithms=self._get_valid_algorithms(),
              leeway=CONF.leeway,
              options={
                  'require_exp': True,
                  'verify_aud': False,
                  'verify_exp': True,
                  'verify_iss': False,
            })

          elif jwt_header['alg'].startswith('HS'):
            jwt_payload = jwt.decode(authorization_header_arr[1],
              key=CONF.verify_signature_secret,
              algorithms=self._get_valid_algorithms(),
              leeway=CONF.leeway,
              options={
                  'require_exp': True,
                  'verify_aud': False,
                  'verify_exp': True,
                  'verify_iss': False,
            })

          else:
            raise jwt.exceptions.InvalidAlgorithmError('Unsupported algorithm given')


          if CONF.verify_issuer:
            if not 'iss' in jwt_payload:
              raise jwt.exceptions.InvalidIssuerError('Invalid issuer')

            if not jwt_payload['iss'] in self._get_valid_issuers():
              raise jwt.exceptions.InvalidIssuerError('Invalid issuer')

        except (jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError,
          jwt.exceptions.ImmatureSignatureError, jwt.exceptions.InvalidAlgorithmError,
          jwt.exceptions.InvalidAudienceError, jwt.exceptions.InvalidIssuedAtError,
          jwt.exceptions.InvalidIssuerError, jwt.exceptions.InvalidKeyError,
          jwt.exceptions.InvalidTokenError, jwt.exceptions.MissingRequiredClaimError) as e:

          raise exception.Unauthorized('JWT Error: ' + e.message)



        response_data = mapped.handle_unscoped_token(auth_payload,
                                              PROVIDERS.resource_api,
                                              PROVIDERS.federation_api,
                                              PROVIDERS.identity_api,
                                              PROVIDERS.assignment_api,
                                              PROVIDERS.role_api,
                                              jwt_payload)

        return base.AuthHandlerResponse(status=True, response_body=None, response_data=response_data)


    def _get_valid_algorithms(self):
      res = [ ]
      for v in CONF.valid_algorithms.split(','):
        v = v.strip()
        if v != '':
          res.append(v)
      return res

    def _get_valid_issuers(self):
      res = [ ]
      for v in CONF.verify_issuer_valid_issuers.split(','):
        v = v.strip()
        if v != '':
          res.append(v)
      return res      

    def _load_public_key(self):
        if not self._public_key:
            with open(CONF.verify_signature_public_key_path, "rb") as key_file:
                self._public_key = serialization.load_pem_public_key(key_file.read(), backend=default_backend())

        return self._public_key

