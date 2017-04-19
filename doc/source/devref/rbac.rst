=================
RBAC in OpenStack
=================

There has historically been much confusion around policy. This tries to clear
up some of that confusing, but creating some shared context around the
problems policy is trying to solve.

RBAC in Pike
============

Lets take a look at RBAC during the Pike Release.

Key Concepts
------------

Key points:

* Keystone owns the concept of a ``user`` how you authenticate users.
* In keystone you can assign a ``role`` to a ``user`` for a ``project``.
  We can consider this as an operator delegating a specific level of access
  to the given user.
* Once you have one or more ``role`` assignments in a given ``project`` a user
  can produce a token scoped to the given project, that lists those roles.
  This token is used to prove the user is authenticated, and the level of
  access they have been granted in that token (i.e. the specific project
  and associated roles)
* When access a service, keystone middleware validates the token, and passes
  the user_id, project_id and a list of the assigned roles using
  ``oslo.context`` to the service. The check is purely that the token is
  valid, and we get the information about that token. There is no check of
  the service catalog, or roles, or anything else in that token.
* Some services use ``oslo.polcy`` to test the ``context`` against a set of
  deployer configurable tests encoded in a ``policy.yaml`` or ``policy.json``
  file
* Some projects ship with an example ``policy.json`` file that operators use
  to protect their system.
* More recently some projects have moved their default policy into code, so
  the policy file need only contain override values, much like how
  configuration works.
* Role names are arbitrary strings, that can be chosen by the operator.
  However the default policy settings mean some roles have a special
  meaning by default.
* If a user has access to several projects, they need to have a different
  scoped token to do operations in each of those projects. Also note, each
  token has a totally independent set of roles.

There have been some loose conventions:

* Most resources are owned by projects, and not the specific user that created
  the resource. But some resources are specific to users.
* Many project allow access to most operations to any project scoped token,
  regardless of the roles assigned to them
* Many projects give users that have the role ``admin`` full access to modify
  things across all projects, regardless of what project they are given that
  role.

Other Concepts
--------------

Some other interesting things we have in place today.

* implied roles allows you to assign a role "foo" that implies you
  also have the roles "bar" and "baz"

* is_admin_project=True means the token is for a project that is considered
  as the "special" admin project, such that any roles that token has should
  be considered global to the system. This concept has not yet been adopted
  by many projects that check the context.

Unsolved user problems
----------------------

Some interesting problems:

* User wants to grant a user in a project to only have access to one of the
  services, such as access to Swift, but no access to any other service.

* Users would like to differentiate between having admin access across the
  whole system, and having admin access to a subset of the system. (This is
  linked to the discussions around hierarchical quotas and delegating quota
  assignment to people closer to the problem that the wider cloud admin,
  helping to scale the operations of your cloud.)

* Various users have customized OpenStack to add RBAC controls that would be
  great to have in the default policy settings:

    * observer of a project: per-project read-only
    * observer of whole system: global read-only
    * a per project user that isn't allowed to do any constructive actions

* Operators can change the API in strange ways by changing the "target" checks
  in the policy file. Sometimes this is on purpose, sometimes its accidental.
  Either way, it usually causes bad things to happen.

* Users want to allow scripts or other applications access to the their
  account to control resources on their behalf. Ideally we want this to happen
  in a way that doesn't violate the concept of "least privilege". More context
  can be found here:
  https://governance.openstack.org/tc/resolutions/20170317-cloud-applications-mission.html

* Services today largely ignore the concept of nested projects, and the role
  assignment currently seems largely independent of the nested projects. This
  isn't really how users expected the delegation of permissions to work.

TODO...

The Future
==========

... and how to get there.

Breaking down the problems
--------------------------

What is the token "scope":

* Every resource in the system has a scope, be it to the project, the
  user, or to a particular user and project combination. The idea is
  you only allow access to that resource if the token the user presents
  has access to that "scope".
* Today the roles and the token are both scoped to the project
* The "admin" role currently violates scoping a token to a project and
  you get a master token.
* is_admin_project attempts to allow a special project to mean
  the token has a scope.


Ideas
------

Lets consider global roles and tokens:

* consider the unscoped token a "global" token
* ability to add a role globally, i.e. give roles to the unscoped token

This could replace the is_admin_project hack.

TODO...

