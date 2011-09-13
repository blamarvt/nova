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

from sqlalchemy import Column, Integer, MetaData, String, Table, ForeignKey


meta = MetaData()


def upgrade(migrate_engine):
    migrate_engine.echo = True
    meta.bind = migrate_engine

    instances = Table('instances', meta, autoload=True,
                      autoload_with=migrate_engine)

    # generate map of instance ids to uuids, generating them where necessary
    mapping = {}
    for instance in migrate_engine.execute(instances.select()):
        mapping[instance.id] = instance.uuid or utils.gen_uuid()

    table_names = ['fixed_ips']

    for table_name in table_names:
        # autoload each table
        table = Table(table_name, meta, autoload=True,
                      autoload_with=migrate_engine)

        # create instance_uuid column and append to each table
        table_instance_uuid = Column('instance_uuid',
                                     String(36),
                                     ForeignKey('instances.uuid'),
                                     nullable=True)
        table_instance_uuid.create(table)

        # iterate over instance ids/uuids and update current table
        for instance_id, instance_uuid in mapping.iteritems():
            query = table.update().\
                          where(table.c.instance_id == instance_id).\
                          values(instance_uuid = instance_uuid)
            migrate_engine.execute(query)

        # drop old instance_id column
        table.c.instance_id.drop()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
