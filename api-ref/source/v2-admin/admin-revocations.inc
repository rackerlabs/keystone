.. -*- rst -*-

=============
 Revocations
=============


Allows the retrieval of revoked tokens.


Show Revoked Tokens (v2)
========================

.. rest_method:: GET /v2.0/tokens/revoked

Show the revoked tokens.

Normal response codes: 200

Error response codes: 401, 500

Response Example
----------------

.. literalinclude:: ./samples/admin/revoked-tokens-response.json
   :language: javascript
