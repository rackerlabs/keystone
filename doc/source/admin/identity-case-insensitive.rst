==============================
Case-Insensitivity in keystone
==============================

Keystone currently handles the case-sensitivity for the naming of each
resource a bit differently, depending on the resource itself and the
backend used. For example, depending on whether a user is backed by
local SQL or LDAP, the case-sensitvity can be different. In cases of
case-insensitivity, the case is preserved, so a Project with the name
"myProject" will not end up becoming either all lower or upper case.

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

Role names are case-insensitive. for example, when keystone bootstraps default
roles, it creates `admin`, `member`, and `reader`. If another role `Member`
(note the upper case 'M') is created, keystone will return a `409` conflict
since it considers the name "Member" == "member".

Backends
========

For each of these examples, we will refer to a project called "mYpRoJeCt" and
user with the name "mYuSeR".

MySQL & SQLite
--------------

By default, MySQL/SQLite are case-insensitive by default, but case-preserving
for `varchar`. This means that setting a project name of "mYpRoJeCt" will
cause attempting to create a new project named "myproject" to fail with
keystone returning a 409 conflict, however, the value of "mYpRoJeCt" will
still be returned.

PostgreSQL
----------

PostgreSQL is case-sensitive by default, so if a project by the name of
"myproject" is created with the existing "mYpRoJeCt", it will be created
successfully.

LDAP
----
