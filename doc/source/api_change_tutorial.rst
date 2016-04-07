..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

API Change Tutorial
===================

This document will guide you through the process of proposing and submitting
and API change in keystone.

Prerequisites
-------------

In order to follow this tutorial, it is assumed that you have read our
`developer guide`_ and `architecture`_ documents.

.. _`developer guide`: http://docs.openstack.org/developer/keystone/developing.html
.. _`architecture`: http://docs.openstack.org/developer/keystone/architecture.html

Proposing a change
------------------

You need to submit a specification against the `keystone-specs`_ repository and
bring it up to discussion with the `keystone core team`_ for agreement.

.. _`keystone-specs`: https://git.openstack.org/cgit/openstack/keystone-specs/
.. _`keystone core team`: https://review.openstack.org/#/admin/groups/9,members

Create
~~~~~~

#. git clone https://git.openstack.org/openstack/keystone-specs ;
#. Use the provided `template`_ ;
#. Push to gerrit for review ;
#. Propose agenda items to the `keystone meeting`_, and make sure someone
   who understands the subject can attend the meeting to answer questions.

.. _`template`: https://git.openstack.org/cgit/openstack/keystone-specs/tree/specs/template.rst
.. _`keystone meeting`: https://wiki.openstack.org/wiki/Meetings/KeystoneMeeting

Agreement
~~~~~~~~~

The `keystone core team`_ will evaluate the specification and vote on accepting
it or not. If accepted, the proposal will be targeted to a release; otherwise,
the specification will be abandoned.

As soon as there is an agreement on the specification, the change may start
rolling out.

Implementing a change
---------------------

In this section, let's assume that a specification proposing the addition of a
`description` field to roles was accepted. In the next subsections, you will
find a detailed explanation on the needed code changes to the keystone code to
implementh such change.

TODO(samueldmq): describe the fun part here :)