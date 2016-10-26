.. -*- rst -*-

============
 OS-PKI API
============


Allows the retrieval of revoked tokens.
Requires v3.0+ of the Identity API.


Show Revoked Tokens
===================

.. rest_method:: GET /v3/auth/tokens/OS-PKI/revoked

Show the revoked tokens.

Normal response codes: 200

Error response codes: 401, 500

Response Example
----------------

.. literalinclude:: ./samples/OS-PKI/revoked-tokens-response.json
   :language: javascript
