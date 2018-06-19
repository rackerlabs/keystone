==============================
Case-Insensitivity in keystone
==============================

Keystone currently handles the case-sensitivity for the naming of each
resource a bit differently, depending on the resource itself and the
backend used. For example, depending on whether a user is backed by
local SQL or LDAP, the case-sensitvity can be different.

Users
=====

Projects
========

If a project with the name `Foobar` already exists, then the following call
which creates a new project by the name of `foobar` will return a 409:

.. code-block:: console

    POST /v3/projects {name: foobar}

Roles
=====

Backends
========

MySQL
-----

PostgreSQL
----------

LDAP
----
