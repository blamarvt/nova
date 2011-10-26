# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2011 OpenStack LLC.
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

import itertools

from nova import flags
from nova import log as logging
from nova.api.openstack import common


FLAGS = flags.FLAGS
LOG = logging.getLogger('nova.api.openstack.views.addresses')


class ViewBuilder(common.ViewBuilder):
    """Models server addresses as a dictionary."""

    _resource_name = "addresses"

    def ip_view(self, ip):
        """Return a dictionary describing an IP address."""
        return {
            "version": ip["version"],
            "addr": ip["addr"],
        }

    def show_view(self, network, label):
        """Returns a dictionary describing a network."""
        return {label: [self.ip_view(ip) for ip in network["ips"]]}

    def index_view(self, networks):
        """Return a dictionary describing a list of networks."""
        addresses = {}
        for label, network in networks.items():
            network_dict = self.show_view(network, label)
            addresses[label] = network_dict[label]
        return dict(addresses=addresses)
