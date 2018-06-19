==============================
Case-Insensitivity in keystone
==============================

(sample intro)

If a project with the name `Foobar` already exists, then the following call
which creates a new project by the name of `foobar` will return a 409:

.. code-block:: ini

    POST /v3/projects {name: foobar}

(specify that this is global across keystone with default mysql)

