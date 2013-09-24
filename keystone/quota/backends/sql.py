# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

import datetime
from sqlalchemy import and_
from sqlalchemy import or_
import sqlalchemy.sql.expression as expression
import uuid

import keystone.common.sql as sql
from keystone import exception
from keystone.quota import core


class QuotasModel(sql.ModelBase):
    __tablename__ = 'quota'
    id = sql.Column(sql.String(64), primary_key=True)
    resource = sql.Column(sql.String(255), nullable=False)
    ceiling = sql.Column(sql.Integer, nullable=False)
    available = sql.Column(sql.Integer, nullable=True)
    created_at = sql.Column(sql.DateTime, nullable=False)
    created_by = sql.Column(sql.String(255), nullable=False)
    closed_at = sql.Column(sql.DateTime, nullable=True)
    closed_by = sql.Column(sql.String(255), nullable=True)

    def __init__(self, uuid, resource, ceiling, available, created_at,
                 created_by):
        self.id = uuid
        self.resource = resource
        self.ceiling = ceiling
        self.available = available
        self.created_at = created_at
        self.created_by = created_by


class ChildFieldDataModel(sql.ModelBase):
    __tablename__ = 'child_field_data'
    id = sql.Column(sql.String(64), primary_key=True)
    quota_id = sql.Column(sql.String(64), sql.ForeignKey('quota.id'),
                          nullable=False)
    key = sql.Column(sql.Text, nullable=False)
    value = sql.Column(sql.Text, nullable=False)


class ParentFieldDataModel(sql.ModelBase):
    __tablename__ = 'parent_field_data'
    id = sql.Column(sql.String(64), primary_key=True)
    quota_id = sql.Column(sql.String(64), sql.ForeignKey('quota.id'),
                          nullable=False)
    key = sql.Column(sql.Text, nullable=False)
    value = sql.Column(sql.Text, nullable=False)


class HistoryQuotasModel(sql.ModelBase):
    __tablename__ = 'h_quota'
    id = sql.Column(sql.String(64), primary_key=True)
    quota_id = sql.Column(sql.String(64), sql.ForeignKey('quota.id'),
                          nullable=False)
    updated_at = sql.Column(sql.DateTime, nullable=False)
    updated_by = sql.Column(sql.Text, nullable=False)
    remark = sql.Column(sql.Text, nullable=False)


class Quotas(sql.Base, core.Driver):
    def db_sync(self, version=None):
        sql.migration.db_sync(version=version)

    def __get_quota_ids_for_child(self, child_data, services, session,
                                  resource=None, get_only_query=False):

            key_value_match = []
            for key, value in child_data.iteritems():
                key_value_match.append(expression.
                                       and_(ChildFieldDataModel.key == key,
                                            ChildFieldDataModel.value ==
                                            value))
            resource_match = []
            if (resource is None):
                for service in services:
                    resource_match.append(QuotasModel.resource.like
                                          (service + ".%"))
            else:
                resource_match.append(QuotasModel.resource ==
                                      (str(services[0]) + "." + resource))

            subquery = (session.query(ChildFieldDataModel.quota_id)
                .filter(and_(ChildFieldDataModel.quota_id == QuotasModel.id))
                .filter(or_(*resource_match))
                .filter(or_(*key_value_match))
                .filter(QuotasModel.closed_at == None)
                .group_by(ChildFieldDataModel.quota_id)) # flake8: noqa

            query = (session.query(ChildFieldDataModel.quota_id)
                .filter(ChildFieldDataModel.quota_id.in_(subquery))
                .group_by(ChildFieldDataModel.quota_id))

            if get_only_query:
                return query

            rows = query.all()
            quota_ids = []
            for row in rows:
                quota_ids.append(str(row.quota_id))
            return quota_ids

    def set_quota(self, resource_name, ceiling, child_data, parent_data,
                  created_by):
        service, resource = resource_name.split('.')

        session = self.get_session()
        with session.begin():
            # First check whether quota for the child iexists
            quota_ids = self.__get_quota_ids_for_child(child_data, [service],
                                                       session, resource)
            if (len(quota_ids) != 0):  # record for quota exist
                parents = (session.query(ParentFieldDataModel.key,
                                        ParentFieldDataModel.value)
                    .filter(ParentFieldDataModel.quota_id == quota_ids[0])
                    .all())
                for parent in parents:
                    if (parent.key in parent_data) and (parent_data[parent.key]
                                                        == parent.value):
                            continue
                    else:
                        raise exception.ForbiddenAction()
                result = (session.query(QuotasModel.ceiling)
                    .filter(QuotasModel.id == quota_ids[0]).one())

                (session.query(QuotasModel)
                    .filter(QuotasModel.id == quota_ids[0])
                    .update({"ceiling": ceiling}))

                remark = "ceiling: %s -> %s." % (result.ceiling, ceiling)
                self.__add_history(session, quota_ids[0], remark, created_by)
            else:
                ref = QuotasModel(str(uuid.uuid4()),
                                  resource=resource_name,
                                  ceiling=ceiling,
                                  available=-1,
                                  created_at=datetime.datetime.now(),
                                  created_by=str(created_by))
                session.add(ref)
                session.flush()
                self.__add_child(session, ref.id, child_data)
                self.__add_child(session, ref.id, parent_data)

    def __add_child(self, session, quota_id, child):
        for key, value in child.iteritems():
            ref = ChildFieldDataModel(id=str(uuid.uuid4()),
                                      quota_id=quota_id,
                                      key=key, value=value)
            session.add(ref)
        session.flush

    def __add_parent(self, session, quota_id, parent):
        for key, value in parent.iteritems():
            ref = ParentFieldDataModel(id=str(uuid.uuid4()),
                                       quota_id=quota_id,
                                       key=key, value=value)
            session.add(ref)
        session.flush()

    def __add_history(self, session, quota_id, remark, created_by):
        ref = HistoryQuotasModel(id=str(uuid.uuid4()),
                                 quota_id=quota_id, remark=remark,
                                 updated_at=datetime.datetime.now(),
                                 updated_by=str(created_by))
        session.add(ref)
        session.flush()

    def get_quota_by_services(self, services, child_data):
        """Gets the quota applicable to the specified child
        for all the resources in the given services

        :param service_list: list of services
        :param child: details of the entity for which quota is requested.
                      It should be a dictionary
        """
        session = self.get_session()
        with session.begin():
            quota_ids = self.__get_quota_ids_for_child(child_data, services,
                                                       session, None, True)
            quotas = (session.query(QuotasModel.resource, QuotasModel.ceiling)
                .filter(QuotasModel.id.in_(quota_ids))
                .order_by(QuotasModel.resource).all())
            services.sort()
            services_quotas = {}
            for service in services:
                resources_quotas = {}
                for quota in quotas:
                    service_name, resource_name = quota.resource.split('.')
                    if (str(service_name) == service):
                        resources_quotas[str(resource_name)] = quota.ceiling
                if len(resources_quotas) != 0:
                    services_quotas[service] = resources_quotas
        return services_quotas

    def delete_quota(self, services, child, deleted_by):
        """Deletes the quota applicable to the specified child
        for all the resources in the mentioned services

        :param service_list: list of services
        :param child: details of the entity for which quota is to be deleted.
                      It should be a dictionary
        """
        session = self.get_session()
        with session.begin():
            quota_ids = self.__get_quota_ids_for_child(child, services,
                                                       session, None, False)
            for quota_id in quota_ids:
                (session.query(QuotasModel)
                    .filter(QuotasModel.id == str(quota_id))
                    .update({"closed_at": datetime.datetime.now(),
                           "closed_by": str(deleted_by)}))
            session.flush()

    def set_domain_quota(self, resource_name, ceiling, domain_id, region_name,
                         parent_data, created_by):
        child_data = {}
        child_data["domain-id"] = domain_id
        child_data["region"] = region_name

        return self.set_quota(resource_name, ceiling, child_data, parent_data,
                              created_by)

    def delete_domain_quota(self, service_list, domain_id, region_name,
                            deleted_by):
        """Deletes the domain quota applicable to the specified region
        within the specified domain for all the resources
        in the mentioned services

        :param service_list: list of services
        :param domain_id: domain-id of the domain
                          for which quota is to be deleted
        :param region_name: name of the region with the mentioned domain-id
                            for which quota is to be deleted
        """
        child_data = {}
        child_data["domain-id"] = domain_id
        child_data["region"] = region_name
        return self.delete_quota(service_list, child_data, deleted_by)

    def get_domain_quota_by_services(self, service_list, domain_id,
                                     region_name):
        """Gets the domain quota applicable to the specified region
        within the specified domain for all the resources
        in the mentioned services

        :param service_list: list of services
        :param domain_id: domain-id of the domain
                          for which quota is to be obtained
        :param region_name: name of the region with the mentioned domain-id
                            for which quota is to be obtained
        """
        child_data = {}
        child_data["domain-id"] = domain_id
        child_data["region"] = region_name
        return self.get_quota_by_services(service_list, child_data)
