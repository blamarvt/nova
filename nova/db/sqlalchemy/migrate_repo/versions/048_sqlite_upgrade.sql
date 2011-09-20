BEGIN TRANSACTION;

-- START fixed_ips
ALTER TABLE fixed_ips RENAME TO fixed_ips_backup;

CREATE TABLE fixed_ips (
    id INTEGER NOT NULL,
    address VARCHAR(255),
    virtual_interface_id INTEGER,
    network_id INTEGER,
    instance_uuid VARCHAR(255),
    allocated BOOLEAN default FALSE,
    leased BOOLEAN default FALSE,
    reserved BOOLEAN default FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    deleted_at DATETIME,
    deleted BOOLEAN NOT NULL, host VARCHAR(255),
    PRIMARY KEY (id),
    FOREIGN KEY(instance_uuid) REFERENCES instances (uuid),
    FOREIGN KEY(virtual_interface_id) REFERENCES virtual_interfaces (id),
    CHECK (deleted IN (0, 1))
);

INSERT INTO fixed_ips
    SELECT * FROM fixed_ips_backup;

UPDATE fixed_ips 
    SET instance_uuid = (
        SELECT uuid FROM instances WHERE id = fixed_ips.instance_uuid
    );

DROP TABLE fixed_ips_backup;
-- END fixed_ips


-- START security_group_instance_association
ALTER TABLE security_group_instance_association 
    RENAME TO security_group_instance_association_backup;

CREATE TABLE security_group_instance_association (
    id INTEGER NOT NULL, 
    security_group_id INTEGER, 
    instance_uuid VARCHAR(36), 
    created_at DATETIME, 
    updated_at DATETIME, 
    deleted_at DATETIME, 
    deleted BOOLEAN, 
    PRIMARY KEY (id), 
    FOREIGN KEY(instance_uuid) REFERENCES instances (uuid), 
    FOREIGN KEY(security_group_id) REFERENCES security_groups (id), 
    CHECK (deleted IN (0, 1))
);

INSERT INTO security_group_instance_association
    SELECT * FROM security_group_instance_association_backup;

UPDATE security_group_instance_association
    SET instance_uuid = (
        SELECT uuid FROM instances WHERE id = security_group_instance_association.instance_uuid
    );

DROP TABLE security_group_instance_association_backup;
-- END security_group_instance_association


-- START volumes
ALTER TABLE volumes RENAME TO volumes_backup;

CREATE TABLE volumes (
    created_at DATETIME, 
    updated_at DATETIME, 
    deleted_at DATETIME, 
    deleted BOOLEAN, 
    id INTEGER NOT NULL, 
    ec2_id VARCHAR(255), 
    user_id VARCHAR(255), 
    project_id VARCHAR(255), 
    host VARCHAR(255), 
    size INTEGER, 
    availability_zone VARCHAR(255), 
    instance_uuid VARCHAR(36),
    mountpoint VARCHAR(255), 
    attach_time VARCHAR(255), 
    status VARCHAR(255), 
    attach_status VARCHAR(255), 
    scheduled_at DATETIME, 
    launched_at DATETIME, 
    terminated_at DATETIME, 
    display_name VARCHAR(255), 
    display_description VARCHAR(255), 
    provider_location VARCHAR(256), 
    provider_auth VARCHAR(256), 
    snapshot_id INTEGER, 
    volume_type_id INTEGER, 
    PRIMARY KEY (id), 
    FOREIGN KEY(instance_uuid) REFERENCES instances (uuid), 
    CHECK (deleted IN (0, 1))
);

INSERT INTO volumes SELECT * FROM volumes_backup;

UPDATE volumes
    SET instance_uuid = (
        SELECT uuid FROM instances WHERE id = volumes.instance_uuid
    );

DROP TABLE volumes_backup;
-- END volumes


-- START block_device_mapping
ALTER TABLE block_device_mapping RENAME TO block_device_mapping_backup;

CREATE TABLE block_device_mapping (
    created_at DATETIME, 
    updated_at DATETIME, 
    deleted_at DATETIME, 
    deleted BOOLEAN, 
    id INTEGER NOT NULL, 
    instance_uuid VARCHAR(36) NOT NULL, 
    device_name VARCHAR(255) NOT NULL, 
    delete_on_termination BOOLEAN, 
    virtual_name VARCHAR(255), 
    snapshot_id INTEGER, 
    volume_id INTEGER, 
    volume_size INTEGER, 
    no_device BOOLEAN, 
    PRIMARY KEY (id), 
    FOREIGN KEY(snapshot_id) REFERENCES snapshots (id), 
    FOREIGN KEY(volume_id) REFERENCES volumes (id), 
    FOREIGN KEY(instance_uuid) REFERENCES instances (uuid), 
    CHECK (delete_on_termination IN (0, 1)), 
    CHECK (deleted IN (0, 1)), 
    CHECK (no_device IN (0, 1))
);

INSERT INTO block_device_mapping SELECT * FROM block_device_mapping_backup;

UPDATE block_device_mapping
    SET instance_uuid = (
        SELECT uuid FROM instances WHERE id = block_device_mapping.instance_uuid
    );

DROP TABLE block_device_mapping_backup;
-- END block_device_mapping


-- START virtual_interfaces
ALTER TABLE virtual_interfaces RENAME TO virtual_interfaces_backup;

CREATE TABLE virtual_interfaces (
    created_at DATETIME, 
    updated_at DATETIME, 
    deleted_at DATETIME, 
    deleted BOOLEAN, 
    id INTEGER NOT NULL, 
    address VARCHAR(255), 
    network_id INTEGER, 
    instance_uuid VARCHAR(36),
    uuid VARCHAR(36), 
    PRIMARY KEY (id), 
    FOREIGN KEY(network_id) REFERENCES networks (id), 
    UNIQUE (address), 
    CHECK (deleted IN (0, 1))
);

INSERT INTO virtual_interfaces SELECT * FROM virtual_interfaces_backup;

UPDATE virtual_interfaces
    SET instance_uuid = (
        SELECT uuid FROM instances WHERE id = virtual_interfaces.instance_uuid
    );

DROP TABLE virtual_interfaces_backup;
-- END virtual_interfaces


-- START instance_metadata
ALTER TABLE instance_metadata RENAME TO instance_metadata_backup;

CREATE TABLE instance_metadata (
    created_at DATETIME, 
    updated_at DATETIME, 
    deleted_at DATETIME, 
    deleted BOOLEAN, 
    id INTEGER NOT NULL, 
    instance_uuid VARCHAR(36),
    key VARCHAR(255), 
    value VARCHAR(255), 
    PRIMARY KEY (id), 
    FOREIGN KEY(instance_uuid) REFERENCES instances (uuid), 
    CHECK (deleted IN (0, 1))
);

INSERT INTO instance_metadata SELECT * FROM instance_metadata_backup;

UPDATE instance_metadata
    SET instance_uuid = (
        SELECT uuid FROM instances WHERE id = instance_metadata.instance_uuid
    );

DROP TABLE instance_metadata_backup;
-- END instance_metadata

COMMIT;