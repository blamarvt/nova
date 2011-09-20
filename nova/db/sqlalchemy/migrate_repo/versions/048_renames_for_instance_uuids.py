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

import migrate
import sqlalchemy

from nova import utils


meta = sqlalchemy.MetaData()


table_names = [
    'instance_actions',
    'block_device_mapping',
    'fixed_ips',
    'security_group_instance_association',
    'volumes',
    'instance_metadata',
    'virtual_interfaces',
]


def upgrade(migrate_engine):
    """Upgrade database schema."""
    meta.bind = migrate_engine

    instances = sqlalchemy.Table('instances', meta, autoload=True)

    sqlalchemy.Index('uuid_idx', instances.c.uuid).create(bind=migrate_engine)

    mapping = {}
    for instance in migrate_engine.execute(instances.select()):
        mapping[instance.id] = instance.uuid or utils.gen_uuid()

    for table_name in table_names:
        # Load table definition
        table = sqlalchemy.Table(table_name, meta, autoload=True)
        instance_uuid_column = sqlalchemy.Column('instance_uuid',
                                                 sqlalchemy.String(36))

        # Add a new instance_uuid column
        table.create_column(instance_uuid_column)

        if table_name != 'virtual_interfaces':
            migrate.ForeignKeyConstraint([table.c.instance_uuid],
                                         [instances.c.uuid]).create()

        # Insert correct uuid data
        for instance_id, instance_uuid in mapping.iteritems():
            query = table.update().\
                          where(table.c.instance_id == instance_id).\
                          values(instance_uuid = instance_uuid)
            migrate_engine.execute(query)

        # Drop the old instance_id column
        table.c.instance_id.drop()


def downgrade(migrate_engine):
    """Downgrade database schema."""
    meta.bind = migrate_engine

    instances = sqlalchemy.Table('instances', meta, autoload=True)

    mapping = {}
    for instance in migrate_engine.execute(instances.select()):
        mapping[instance.uuid] = instance.id

    for table_name in table_names:
        # Load table definition
        table = sqlalchemy.Table(table_name, meta, autoload=True)
        instance_id_column = sqlalchemy.Column('instance_id',
                                               sqlalchemy.Integer())

        # Add a new instance_id column
        table.create_column(instance_id_column)

        # Insert correct uuid data
        for instance_uuid, instance_id in mapping.iteritems():
            query = table.update().\
                          where(table.c.instance_uuid == instance_uuid).\
                          values(instance_id = instance_id)
            migrate_engine.execute(query)

        if table_name != 'virtual_interfaces':
            migrate.ForeignKeyConstraint([table.c.instance_uuid],
                                         [instances.c.uuid]).drop()

        # Drop the old instance_id column
        table.c.instance_uuid.drop()

        if table_name != 'virtual_interfaces':
            migrate.ForeignKeyConstraint([table.c.instance_id],
                                         [instances.c.id]).create()

    sqlalchemy.Index('uuid_idx', instances.c.uuid).drop(bind=migrate_engine)
