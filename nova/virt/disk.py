# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
#
# Copyright 2011, Piston Cloud Computing, Inc.
#
# All Rights Reserved.
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
"""
Utility methods to resize, repartition, and modify disk images.

Includes injection of SSH PGP keys into authorized_keys file.

"""

import json
import os
import tempfile
import time

from nova import context
from nova import db
from nova import exception
from nova import flags
from nova import log as logging
from nova import utils


LOG = logging.getLogger('nova.compute.disk')
FLAGS = flags.FLAGS
flags.DEFINE_integer('minimum_root_size', 1024 * 1024 * 1024 * 10,
                     'minimum size in bytes of root partition')
flags.DEFINE_integer('block_size', 1024 * 1024 * 256,
                     'block_size to use for dd')
flags.DEFINE_string('injected_network_template',
                    utils.abspath('virt/interfaces.template'),
                    'Template file for injected network')
flags.DEFINE_integer('timeout_nbd', 10,
                     'time to wait for a NBD device coming up')
flags.DEFINE_integer('max_nbd_devices', 16,
                     'maximum number of possible nbd devices')

# NOTE(yamahata): DEFINE_list() doesn't work because the command may
#                 include ','. For example,
#                 mkfs.ext3 -O dir_index,extent -E stride=8,stripe-width=16
#                 --label %(fs_label)s %(target)s
#
#                 DEFINE_list() parses its argument by
#                 [s.strip() for s in argument.split(self._token)]
#                 where self._token = ','
#                 No escape nor exceptional handling for ','.
#                 DEFINE_list() doesn't give us what we need.
flags.DEFINE_multistring('virt_mkfs',
                         ['windows=mkfs.ntfs --fast --label %(fs_label)s '
                          '%(target)s',
                          # NOTE(yamahata): vfat case
                          #'windows=mkfs.vfat -n %(fs_label)s %(target)s',
                          'linux=mkfs.ext3 -L %(fs_label)s -F %(target)s',
                          'default=mkfs.ext3 -L %(fs_label)s -F %(target)s'],
                         'mkfs commands for ephemeral device. The format is'
                         '<os_type>=<mkfs command>')


_MKFS_COMMAND = {}
_DEFAULT_MKFS_COMMAND = None


for s in FLAGS.virt_mkfs:
    # NOTE(yamahata): mkfs command may includes '=' for its options.
    #                 So item.partition('=') doesn't work here
    os_type, mkfs_command = s.split('=', 1)
    if os_type:
        _MKFS_COMMAND[os_type] = mkfs_command
    if os_type == 'default':
        _DEFAULT_MKFS_COMMAND = mkfs_command


def mkfs(os_type, fs_label, target):
    mkfs_command = (_MKFS_COMMAND.get(os_type, _DEFAULT_MKFS_COMMAND) or
                    '') % locals()
    if mkfs_command:
        utils.execute(*mkfs_command.split())


def extend(image, size):
    """Increase image to size"""
    file_size = os.path.getsize(image)
    if file_size >= size:
        return
    utils.execute('qemu-img', 'resize', image, size)
    # NOTE(vish): attempts to resize filesystem
    utils.execute('e2fsck', '-fp', image, check_exit_code=False)
    utils.execute('resize2fs', image, check_exit_code=False)


def _unpartition_device(device_path):
    """Remove partitions created by using _partition_device()."""
    _, error = utils.execute('kpartx', '-d', device_path, run_as_root=True)
    if error:
        raise exception.Error(_('Failed to remove kpartx partitions for '
                                '%(device_path)s: %(error)s' % locals()))


def _partition_device(device_path):
    """Partition a mounted disk-like file using kpartx."""
    _, error = utils.execute('kpartx', '-a', device_path, run_as_root=True)
    if error:
        raise exception.Error(_('Failed to partition %(device_path)s: '
                                '%(error)s') % locals())


def _remove_ext_autocheck(device_path):
    """Remove extX filesystem's 'check this device every XX mounts'."""
    utils.execute('tune2fs', '-c', 0, '-i', 0, device_path, run_as_root=True)


def _mount(device_path, mount_path):
    _, error = utils.execute('mount',
                             device_path,
                             mount_path,
                             run_as_root=True)
    if error:
        raise exception.Error(_('Failed to mount filesystem: '
                                '%(error)s') % locals())


def _write_data(path, data, owner=None, group=None, perms=None, append=False):
    """Write data to the given path.

    :param path: The absolute path to write data to.
    :param data: The data to write to the given path.
    :param owner: The file will be chowned to this user
    :param group: The file will be chowned to belong to this group
    :param perms: Octal number representing permissions (for example 0o700)
    :param append: If True, append to the file instead of overwriting contents

    """
    file_name = os.path.basename(path)
    directory = os.path.dirname(path)

    if not file_name:
        raise exception.Error(_('%s is not a valid file path.') % path)

    try:
        os.makedirs(directory)
    except OSError:
        raise exception.Error(_('Unable to create directory %s') % directory)

    if owner is not None:
        utils.execute('chown', owner, path, run_as_root=True)

    if group is not None:
        utils.execute('chgrp', group, path, run_as_root=True)

    if perms is not None:
        utils.execute('chmod', perms, path, run_as_root=True)

    if append is True:
        utils.execute('tee', '-a', path, process_input=data, run_as_root=True)
    else:
        utils.execute('tee', path, process_input=data, run_as_root=True)


def inject_data(image, inject_data, partition=None, nbd=False, tune2fs=True):
    """Injects data into a disk image.

    Mounts the image as a fully partitioned disk and attempts to inject into
    the specified partition number. If partition is not specified it mounts the
    image as a single partition.

    """
    device_path = _link_device(image, nbd)
    device_name = device.split('/')[-1]

    if partition is not None:
        _partition_device(device)
        device_path = '/dev/mapper/%sp%s' % (device_name, partition)

    if not os.path.exists(device_path):
        raise exception.Error(_('Device %(device_path)s could not be found') %
                                locals())

    if tune2fs:
        _remove_ext_autocheck(device_path)

    tmpdir = tempfile.mkdtemp()
    _mount(device_path, tmpdir)

    for file_object in file_objects:
        path = os.path.normpath(file_object.path)
        full_path = os.path.join(tmpdir, path)
        _write_data(path=full_path,
                    data=file_object.data,
                    owner=file_object.owner,
                    group=file_object.group,
                    perms=file_object.perms)

    _umount(device_path)
    os.rmdir(tmpdir)
    _unpartition_device(device)
    _unlink_device(device, nbd)


def setup_container(image, container_dir=None, nbd=False):
    """Setup the LXC container.

    It will mount the loopback image to the container directory in order
    to create the root filesystem for the container.

    LXC does not support qcow2 images yet.
    """
    try:
        device = _link_device(image, nbd)
        utils.execute('mount', device, container_dir, run_as_root=True)
    except Exception, exn:
        LOG.exception(_('Failed to mount filesystem: %s'), exn)
        _unlink_device(device, nbd)


def destroy_container(target, instance, nbd=False):
    """Destroy the container once it terminates.

    It will umount the container that is mounted, try to find the loopback
    device associated with the container and delete it.

    LXC does not support qcow2 images yet.
    """
    out, err = utils.execute('mount', run_as_root=True)
    for loop in out.splitlines():
        if instance['name'] in loop:
            device = loop.split()[0]

    try:
        container_dir = '%s/rootfs' % target
        utils.execute('umount', container_dir, run_as_root=True)
        _unlink_device(device, nbd)
    except Exception, exn:
        LOG.exception(_('Failed to remove container: %s'), exn)


def _link_device(image, nbd):
    """Link image to device using loopback or nbd"""

    if nbd:
        device = _allocate_device()
        utils.execute('qemu-nbd', '-c', device, image, run_as_root=True)
        # NOTE(vish): this forks into another process, so give it a chance
        #             to set up before continuuing
        for i in xrange(FLAGS.timeout_nbd):
            if os.path.exists("/sys/block/%s/pid" % os.path.basename(device)):
                return device
            time.sleep(1)
        raise exception.Error(_('nbd device %s did not show up') % device)
    else:
        out, err = utils.execute('losetup', '--find', '--show', image,
                                 run_as_root=True)
        if err:
            raise exception.Error(_('Could not attach image to loopback: %s')
                                  % err)
        return out.strip()


def _unlink_device(device, nbd):
    """Unlink image from device using loopback or nbd"""
    if nbd:
        utils.execute('qemu-nbd', '-d', device, run_as_root=True)
        _free_device(device)
    else:
        utils.execute('losetup', '--detach', device, run_as_root=True)


_DEVICES = ['/dev/nbd%s' % i for i in xrange(FLAGS.max_nbd_devices)]


def _allocate_device():
    # NOTE(vish): This assumes no other processes are allocating nbd devices.
    #             It may race cause a race condition if multiple
    #             workers are running on a given machine.

    while True:
        if not _DEVICES:
            raise exception.Error(_('No free nbd devices'))
        device = _DEVICES.pop()
        if not os.path.exists("/sys/block/%s/pid" % os.path.basename(device)):
            break
    return device


def _free_device(device):
    _DEVICES.append(device)


def inject_data_into_fs(fs, key, net, metadata, execute):
    """Injects data into a filesystem already mounted by the caller.
    Virt connections can call this directly if they mount their fs
    in a different way to inject_data
    """
    if key:
        _inject_key_into_fs(key, fs, execute=execute)
    if net:
        _inject_net_into_fs(net, fs, execute=execute)
    if metadata:
        _inject_metadata_into_fs(metadata, fs, execute=execute)


def _inject_metadata_into_fs(metadata, fs, execute=None):
    metadata_path = os.path.join(fs, "meta.js")
    metadata = dict([(m.key, m.value) for m in metadata])

    utils.execute('tee', metadata_path,
                  process_input=json.dumps(metadata), run_as_root=True)


def _inject_key_into_fs(key, fs, execute=None):
    """Add the given public ssh key to root's authorized_keys.

    key is an ssh key string.
    fs is the path to the base of the filesystem into which to inject the key.
    """
    sshdir = os.path.join(fs, 'root', '.ssh')
    utils.execute('mkdir', '-p', sshdir, run_as_root=True)
    utils.execute('chown', 'root', sshdir, run_as_root=True)
    utils.execute('chmod', '700', sshdir, run_as_root=True)
    keyfile = os.path.join(sshdir, 'authorized_keys')
    utils.execute('tee', '-a', keyfile,
                  process_input='\n' + key.strip() + '\n', run_as_root=True)


def _inject_net_into_fs(net, fs, execute=None):
    """Inject /etc/network/interfaces into the filesystem rooted at fs.

    net is the contents of /etc/network/interfaces.
    """
    netdir = os.path.join(os.path.join(fs, 'etc'), 'network')
    utils.execute('mkdir', '-p', netdir, run_as_root=True)
    utils.execute('chown', 'root:root', netdir, run_as_root=True)
    utils.execute('chmod', 755, netdir, run_as_root=True)
    netfile = os.path.join(netdir, 'interfaces')
    utils.execute('tee', netfile, process_input=net, run_as_root=True)
