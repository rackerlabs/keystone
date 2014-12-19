OpenStack Identity API v3 Example Assignment Engine
===================================================

This extension provides an example alternative assignment engine, showing
how the newly split assignment component of Keystone supports such
extensions.

To provide such an example, a simple specific ABAC engine is provided
(MyFirstABAC). This is not a general purpose ABAC engine, but chosen purely
to provide a simple alternate model. It provides the ability to add an age
attribute to a user and to assign role rules to projects - one role if
a user is over eighteen, one if they are under eighteen.

MyFirstABAC replaces the v2 add_role_to_project and v3 grant APIs with the
ones listed below, but still enables the rest of Keystone and OpenStack
(i.e. project authentication) to function as normal.

User Attributes
~~~~~~~~~~~~~~~

Add an age attribute to a user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    PUT /users/{user_id}/OS-MY-FIRST-ABAC/age/{age}

If the user already has an age attribute, that will be overwritten.

Response:

::

    Status: 204 No Content

Get the age of a user
^^^^^^^^^^^^^^^^^^^^^

::

    GET /users/{user_id}/OS-MY-FIRST-ABAC/age

Response:

::

    Status: 200 OK

    {
        "user_attributes": {
            "age": "25",
            "links": {
                "self": "http://identity:35357/v3/users/"--user-id--"/OS-MY-FIRST-ABAC/age
            }
        }
    }

Remove an age attribute from a user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    DEL /users/{user_id}/OS-MY-FIRST-ABAC/age

Response:

::

    Status: 204 No Content


Project Role Rules
~~~~~~~~~~~~~~~~~~

Assign a role to a project for users who are 18 or over
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    PUT /projects/{project_id}/OS-MY-FIRST-ABAC/role_if_18_or_over/{role_id}


Response:

::

    Status: 204 No Content

Assign a role to a project for users who are under 18
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    PUT /projects/{project_id}/OS-MY-FIRST-ABAC/role_if_under_18/{role_id}


Response:

::

    Status: 204 No Content

Get the role rules for a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    GET /projects/{project_id}/OS-MY-FIRST-ABAC/role_rules

Response:

::

    Status: 200 OK

    {
        "project_role_rules": {
            "18_and_over": "--role_id--",
            "links": {
                "self": "http://identity:35357/v3/users/"--user-id--"/OS-MY-FIRST-ABAC/age
            },
            "under_18": "--role_id--",
        }
    }

Deassign a role to a project for users who are 18 or over
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    DEL /projects/{project_id}/OS-MY-FIRST-ABAC/role_if_18_or_over


Response:

::

    Status: 204 No Content

Deassign a role to a project for users who are under 18
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    DEL /projects/{project_id}/OS-MY-FIRST-ABAC/role_if_under_18


Response:

::

    Status: 204 No Content