:tocdepth: 3

--------------------------------------
 Identity API v3 extensions (CURRENT)
--------------------------------------

=============
Relationships
=============

The entries within the operations below contain a relationship link, which
appears as a valid URI, however these are actually
URN (Uniform Resource Name), which are similar to GUID except it uses a URI
syntax so that it is easier to be read. These links do not resolve to
anything valid, but exist to show a relationship.

So an example of finding this URL "relationship" would be:

For a user representation there might be a dictionary key ``relationships``
and the value would map URN to URL. So ``GET /user/1234/`` gives you a user
representation. Then you could do something like
``user['relationships']['http://does-not-exist#user-groups']`` to find a URL
that can be used to retrieve a user's groups.

=======================
Identity API Extensions
=======================

This page describes these Identity API v3 extensions:

* `OS-ENDPOINT-POLICY API`_
* `OS-OAUTH1 API`_
* `OS-TRUST API`_
* `OS-REVOKE API`_
* `OS-EP-FILTER API`_
* `OS-FEDERATION API`_
* `OS-SIMPLE-CERT API`_

.. rest_expand_all::

.. include:: endpoint-policy.inc
.. include:: oauth.inc
.. include:: trust.inc
.. include:: revoke.inc
.. include:: ep-filter.inc
.. include:: federation.inc
.. include:: simple-cert.inc
