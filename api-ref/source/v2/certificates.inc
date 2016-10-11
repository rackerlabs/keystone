.. -*- rst -*-

============
Certificates
============


Allows the retrieval of information for Certificate Authorities and certificates.


Show CA Certificate
===================

.. rest_method:: GET /v2.0/certificates/ca

List the CA for issued certificate.

Normal response codes: 200

Error response codes: 401, 500

Response
--------

Status: 200 OK


Show Signing Certificates
=========================

.. rest_method:: GET /v2.0/certificates/signing

List all available signing certificates.

Normal response codes: 200

Error response codes: 401, 500

Response
--------

Status: 200 OK
