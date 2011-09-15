# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack LLC.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nova import utils

from migrate import ForeignKeyConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import ForeignKey


meta = MetaData()


def prepare_other(migrate_engine):

def upgrade(migrate_engine):
    migrate_engine.echo = True
    meta.bind = migrate_engine

    fixed_ips_table = Table('fixed_ips', meta, autoload=True)

    instance_uuid_column = Column('instance_uuid',
                                  String(36),
                                  ForeignKey('instances.uuid'),
                                  nullable=True)

    fixed_ips_table.create_column(instance_uuid_column)

    instances = Table('instances', meta, autoload=True)
    fixed_ips = Table('fixed_ips', meta, autoload=True)

    # generate map of instance ids to uuids, generating them where necessary
    mapping = {}
    for instance in migrate_engine.execute(instances.select()):
        mapping[instance.id] = instance.uuid or utils.gen_uuid()

    # iterate over instance ids/uuids and update current table
    for instance_id, instance_uuid in mapping.iteritems():
        query = fixed_ips.update().\
                      where(table.c.instance_id == instance_id).\
                      values(instance_uuid = instance_uuid)
        migrate_engine.execute(query)

    # drop old instance_id column
    ForeignKeyConstraint(columns=[fixed_ips.c.instance_id],
                         refcolumns=[instances.c.id]).drop()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
