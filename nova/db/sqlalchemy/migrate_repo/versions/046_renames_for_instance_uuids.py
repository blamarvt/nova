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

from sqlalchemy import Column, Integer, MetaData, String, Table


meta = MetaData()


def upgrade(migrate_engine):
    migrate_engine.echo = True
    meta.bind = migrate_engine

    fixed_ips = Table('fixed_ips', meta, autoload=True,
                      autoload_with=migrate_engine)

    instance_id_column = fixed_ips.c.instance_id
    instance_id_column.alter(type=String(36)) # No idea why this errors
    instance_id_column.alter(name='instance_uuid')


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    fixed_ips = Table('fixed_ips', meta, autoload=True,
                      autoload_with=migrate_engine)

    instance_uuid_column = fixed_ips.c.instance_uuid
    instance_uuid_column.alter(name='instance_id')
