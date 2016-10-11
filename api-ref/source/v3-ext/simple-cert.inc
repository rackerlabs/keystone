.. -*- rst -*-

====================
 OS-SIMPLE-CERT API
====================


Allows the retrieval of information for Certificate Authorities and certificates. Requires v3.0+ of the Identity API.


Show CAs
========

..rest_method:: GET /v3/OS-SIMPLE-CERT/ca

List the CA for issued certificate.

Normal response codes: 200

Error response codes: 401, 500

Response
--------

Status: 200 OK


Show Certificates
=================

..rest_method:: GET /v3/OS-SIMPLE-CERT/certificates

List all available certificates.

Normal response codes: 200

Error response codes: 401, 500

Response
--------

Status: 200 OK
