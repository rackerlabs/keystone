
..
      Copyright 2013 IBM Corp.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

============================
Keystone Event Notifications
============================

Keystone provides notifications about usage data so that 3rd party applications
can use the data for billing, monitoring, or quota purposes.  This document
describes the current inclusions and exclusions for Keystone usage
notifications.


Create/Delete/Update Tenant/User/Role/Domain/Group
==================================================

One notification is sent when a tenant, user, role, domain, or group is
successfully created, deleted, or updated.

The following message is sent when create tenant finishes::

 {"event_type": "identity.resource.created",
  "message_id": "<message ID>",
  "publisher_id": "identity.<hostname>",
  "timestamp": "<timestamp>",
  "priority": "INFO",
  "payload": {<Varies based on resource info>}}

For examples of payloads for these notifications, see `Payload Examples`_.

Notifications for deletes and updates are similar to those for creates, with
``deleted`` or ``updated`` replacing ``created`` in the above notification.

Notifications for user, role, domain and group operations are the same as
those for tenant.

If the operation fails, the notification won't be sent, and no special
error notification will be sent.  Information about the error is handled
through normal exception paths.


Payload Examples
================

This is an example of the payload sent for a tenant creation notification::

 # bpokorny: Will fix the payload info once more testing is done.
 {"resource_info":
   {"name": "network-1",
    "admin_state_up": true}}

