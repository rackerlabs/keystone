# Copyright 2012-13 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from keystone import assignment as keystone_assignment
from keystone.common import sql
from keystone import config
from keystone import exception


CONF = config.CONF


class ABACAssignment(keystone_assignment.Driver):

    def default_role_driver(self):
        return "keystone.assignment.role_backends.sql.Role"

    # First, the set of methods that support the new functionality being
    # provided by this new assignment engine.

    def assign_role_for_18_or_over(self, project_id, role_id):
        with sql.transaction() as session:
            project_attr = session.query(ProjectAttributes).get(project_id)
            if not project_attr:
                session.add(ProjectAttributes(
                    project_id=project_id, role_for_eighteen_or_over=role_id))
            else:
                project_attr.role_for_eighteen_or_over = role_id

    def assign_role_for_under_18(self, project_id, role_id):
        with sql.transaction() as session:
            project_attr = session.query(ProjectAttributes).get(project_id)
            if not project_attr:
                session.add(ProjectAttributes(
                    project_id=project_id, role_for_under_eighteen=role_id))
            else:
                project_attr.role_for_under_eighteen = role_id

    def get_project_role_rules(self, project_id):
        with sql.transaction() as session:
            project_attr = session.query(ProjectAttributes).get(project_id)
            if not project_attr:
                return (None, None)
            else:
                return (project_attr.role_for_under_eighteen,
                        project_attr.role_for_eighteen_or_over)

    def _delete_project_record_if_no_rules(self, project_attr, session):
        if (project_attr.role_for_eighteen_or_over is None and
                project_attr.role_for_under_eighteen is None):
            session.delete(project_attr)

    def deassign_role_for_18_or_over(self, project_id):
        with sql.transaction() as session:
            project_attr = session.query(ProjectAttributes).get(project_id)
            if not project_attr:
                # Re-use ProjectNotFound as an exception
                raise exception.ProjectNotFound(project_id=project_id)
            project_attr.role_for_eighteen_or_over = None
            self._delete_project_record_if_no_rules(project_attr, session)

    def deassign_role_for_under_18(self, project_id):
        with sql.transaction() as session:
            project_attr = session.query(ProjectAttributes).get(project_id)
            if not project_attr:
                # Re-use ProjectNotFound as an exception
                raise exception.ProjectNotFound(project_id=project_id)
            project_attr.role_for_under_eighteen = None
            self._delete_project_record_if_no_rules(project_attr, session)

    def add_age_attribute_to_user(self, user_id, age):
        """Add/Update the age attribute for a user.

        If there is no user attribute existing then create a new entry in the
        UserAttribute table, if there is then overwrite the existing age.

        """
        with sql.transaction() as session:
            user_attr = session.query(UserAttributes).get(user_id)
            if not user_attr:
                session.add(UserAttributes(user_id=user_id, age=age))
            else:
                user_attr.age = age

    def get_age_attribute_for_user(self, user_id):
        """Get the age attribute for a user."""
        with sql.transaction() as session:
            user_attr = session.query(UserAttributes).get(user_id)
            if not user_attr:
                return None
        return(user_attr.age)

    def remove_age_attribute_from_user(self, user_id):
        """Remove the age attribute for a user.

        Since we only support one attribute, we just delete the record.

        """
        with sql.transaction() as session:
            user_attr = session.query(UserAttributes).get(user_id)
            if not user_attr:
                # Re-use UserNotFound as an exception
                raise exception.UserNotFound(user_id=user_id)
            session.delete(user_attr)

    # The set of methods that we must satisfy in order for the rest of Keystone
    # and OpenStack to function. This is typically to generate tokens and
    # provide confirmation of which projects/domains a user has access to.

    def list_user_ids_for_project(self, tenant_id):
        # In this example, all users that have had an age attribute assigned
        # have some kind of role on each project with an age rule.
        with sql.transaction() as session:
            project_attr = session.query(ProjectAttributes).get(tenant_id)
            if not project_attr:
                # No age rules have been assigned, so no user will have access
                return []
            user_attrs = session.query(UserAttributes).all()

        # In this simple model, all users with an appropriate
        # age are included in the list
        user_list = []
        for user_attr in user_attrs:
            if (user_attr.age >= 18 and
                    project_attr.role_for_eighteen_or_over is not None) or (
                user_attr.age < 18 and
                    project_attr.role_for_under_eighteen is not None):
                user_list.append(user_attr.user_id)
        return user_list

    def list_project_ids_for_user(self, user_id, group_ids, hints,
                                  inherited=False):
        with sql.transaction() as session:
            user_attr = session.query(UserAttributes).get(user_id)
            if not user_attr:
                # User hasn't had an age attribute assigned, so no projects
                # for them.
                return []

            project_attrs = session.query(ProjectAttributes).all()

        # In this simple model, all projects with a role for the appropriate
        # age are included in the list
        project_list = []
        for project_attr in project_attrs:
            if (user_attr.age >= 18 and
                    project_attr.role_for_eighteen_or_over is not None) or (
                user_attr.age < 18 and
                    project_attr.role_for_under_eighteen is not None):
                project_list.append(project_attr.project_id)
        return project_list

    def list_role_assignments(self):

        def construct_assignment(project, user, role):
            assignment = {}
            assignment['user_id'] = user.user_id
            assignment['project_id'] = project.project_id
            assignment['role_id'] = role
            return assignment

        with sql.transaction() as session:
            project_attrs = session.query(ProjectAttributes).all()
            user_attrs = session.query(UserAttributes).all()

        assignments = []
        for project_attr in project_attrs:
            for user_attr in user_attrs:
                if (user_attr.age >= 18 and
                        project_attr.role_for_eighteen_or_over is not None):
                    assignments.append(
                        construct_assignment(
                            project_attr, user_attr,
                            project_attr.role_for_eighteen_or_over))
                if (user_attr.age < 18 and
                        project_attr.role_for_under_eighteen is not None):
                    assignments.append(
                        construct_assignment(
                            project_attr, user_attr,
                            project_attr.role_for_under_eighteen))
        return assignments

    def _get_metadata(self, user_id=None, tenant_id=None,
                      domain_id=None, group_id=None, session=None):
        # This method is scheduled for removal during Kilo cleanup, but for
        # now we still need to support it.

        # We aren't given a session when called by the manager directly.
        if session is None:
            session = sql.get_session()

        if user_id is None or tenant_id is None:
            # We only support users and projects in this example
            raise exception.MetadataNotFound()

        user_attr = session.query(UserAttributes).get(user_id)
        project_attr = session.query(ProjectAttributes).get(tenant_id)
        if user_attr is None or project_attr is None:
            # User hasn't had an age attribute assigned, or the project has no
            # rules - in either case we raise MetadataNotFound
            raise exception.MetadataNotFound()

        metadata_ref = {}
        metadata_ref['roles'] = []
        if (user_attr.age >= 18 and
                project_attr.role_for_eighteen_or_over is not None):
            metadata_ref['roles'] = (
                [{'id': project_attr.role_for_eighteen_or_over}])
        elif (user_attr.age < 18 and
                project_attr.role_for_under_eighteen is not None):
            metadata_ref['roles'] = (
                [{'id': project_attr.role_for_under_eighteen}])

        if len(metadata_ref['roles']) == 0:
            raise exception.MetadataNotFound()

        return metadata_ref

    def list_domain_ids_for_user(self, user_id, group_ids, hints,
                                 inherited=False):
        # This example does not support domain attributes
        return []

    def list_role_ids_for_groups_on_domain(self, group_ids, domain_id):
        # This example does not support domain or group attributes
        return []

    def list_role_ids_for_groups_on_project(
            self, groups, project_id, project_domain_id, project_parents):
        # This example does not support group attributes
        return []

    def list_project_ids_for_groups(self, group_ids, hints,
                                    inherited=False):
        # This example does not support group attributes
        return []

    def list_domain_ids_for_groups(self, group_ids, inherited=False):
        # This example does not support domain or group attributes
        return []

    # The set of methods that will be called to clean up assignments from
    # the assignment manager.

    def delete_project_assignments(self, project_id):
        with sql.transaction() as session:
            q = session.query(ProjectAttributes)
            q = q.filter_by(project_id=project_id)
            q.delete(False)

    def delete_domain_assignments(self, domain_id):
        # This example does not support domain attributes
        pass

    def delete_role_assignments(self, role_id):
        # TODO(henry-nash): remove any role rules for the role_id
        pass

    def delete_user(self, user_id):
        with sql.transaction() as session:
            q = session.query(UserAttributes)
            q = q.filter_by(user_id=user_id)
            q.delete(False)

    def delete_group(self, group_id):
        # This example does not support group attributes
        pass

    # The following represent the regular v2/v3 grant APIs, that typically
    # would not be supported by an alternate assignment engine.

    def add_role_to_user_and_project(self, user_id, tenant_id, role_id):
        raise exception.NotImplemented()

    def remove_role_from_user_and_project(self, user_id, tenant_id, role_id):
        raise exception.NotImplemented()

    def create_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):
        raise exception.NotImplemented()

    def check_grant_role_id(self, role_id, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        raise exception.NotImplemented()

    def list_grant_role_ids(self, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        raise exception.NotImplemented()

    def delete_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):
        raise exception.NotImplemented()


# We support a single attribute for users - that of age.
class UserAttributes(sql.ModelBase, sql.ModelDictMixin):
    """User Attributes table."""
    __tablename__ = 'myfirstabac_user_attributes'
    attributes = ['user_id', 'age']
    user_id = sql.Column(sql.String(64), primary_key=True)
    age = sql.Column(sql.Integer, nullable=False)


# We support two rules for projects, basically giving a user a different
# role depending on their age. A real ABAC engine would have a much more
# flexible way of storing such rules, but for this simple example we just hard
# code the rules as SQL columns.
class ProjectAttributes(sql.ModelBase, sql.ModelDictMixin):
    """Project Attributes table."""
    __tablename__ = 'myfirstabac_project_attributes'
    attributes = ['project_id', 'role_for_eighteen_or_over',
                  'role_for_under_eighteen']
    project_id = sql.Column(sql.String(64), primary_key=True)
    role_for_eighteen_or_over = sql.Column(sql.String(64), nullable=True)
    role_for_under_eighteen = sql.Column(sql.String(64), nullable=True)
