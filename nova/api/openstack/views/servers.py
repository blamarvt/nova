# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2011 OpenStack LLC.
# Copyright 2011 Piston Cloud Computing, Inc.
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

import hashlib
import os

from nova.api.openstack import common
from nova.api.openstack import views
from nova.compute import vm_states
from nova import exception
from nova import log as logging
from nova import utils


LOG = logging.getLogger('nova.api.openstack.views.servers')


class ViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _resource_name = "servers"

    _progress_statuses = (
        "ACTIVE",
        "BUILD",
        "REBUILD",
        "RESIZE",
        "VERIFY_RESIZE",
    )

    def __init__(self):
        """Initialize view builder."""
        super(ViewBuilder, self).__init__()
        self._address_builder = views.addresses.ViewBuilder()
        self._flavor_builder = views.flavors.ViewBuilder()
        self._image_builder = views.images.ViewBuilder()

    def _skip_precooked(func):
        def wrapped(self, instance):
            if instance.get("_is_precooked"):
                return dict(server=instance)
            else:
                return func(self, instance)
        return wrapped

    def set_request(self, value):
        self._request = value
        self._address_builder.set_request(value)
        self._flavor_builder.set_request(value)
        self._image_builder.set_request(value)

    def create_view(self, instance):
        """View that should be returned when an instance is created."""
        return {
            "server": {
                "id": instance["uuid"],
                "links": self._get_links(instance["uuid"]),
            },
        }

    @_skip_precooked
    def basic_view(self, instance):
        """Generic, non-detailed view of an instance."""
        return {
            "server": {
                "id": instance["uuid"],
                "name": instance["display_name"],
                "links": self._get_links(instance["uuid"]),
            },
        }

    @_skip_precooked
    def show_view(self, instance):
        """Detailed view of a single instance."""
        server = {
            "server": {
                "id": instance["uuid"],
                "name": instance["display_name"],
                "status": self._get_vm_state(instance),
                "tenant_id": instance.get("project_id") or "",
                "user_id": instance.get("user_id") or "",
                "metadata": self._get_metadata(instance),
                "hostId": self._get_host_id(instance) or "",
                "image": self._get_image(instance),
                "flavor": self._get_flavor(instance),
                "created": utils.isotime(instance["created_at"]),
                "updated": utils.isotime(instance["updated_at"]),
                "addresses": self._get_addresses(instance),
                "accessIPv4": instance.get("access_ip_v4") or "",
                "accessIPv6": instance.get("access_ip_v6") or "",
                "key_name": instance.get("key_name") or "",
                "config_drive": instance.get("config_drive"),
                "links": self._get_links(instance["uuid"]),
            },
        }

        if server["server"]["status"] in self._progress_statuses:
            server["server"]["progress"] = instance.get("progress", 0)

        return server

    def index_view(self, instances):
        """Show a list of servers without many details."""
        list_func = self.basic_view
        return self._list_view(list_func, instances)

    def detail_view(self, instances):
        """Detailed view of a list of instance."""
        list_func = self.show_view
        return self._list_view(list_func, instances)

    def _list_view(self, list_func, servers):
        """Provide a view for a list of servers."""
        server_list = [list_func(server)["server"] for server in servers]
        servers_links = self._get_collection_links(servers)
        servers_dict = dict(servers=server_list)

        if servers_links:
            servers_dict["servers_links"] = servers_links

        return servers_dict

    @staticmethod
    def _get_metadata(instance):
        metadata = instance.get("metadata", [])
        return dict((item['key'], str(item['value'])) for item in metadata)

    @staticmethod
    def _get_vm_state(instance):
        return common.status_from_state(instance.get("vm_state"),
                                        instance.get("task_state"))

    @staticmethod
    def _get_host_id(instance):
        host = instance.get("host")
        if host:
            return hashlib.sha224(host).hexdigest()  # pylint: disable=E1101

    def _get_addresses(self, instance):
        context = self.request.environ["nova.context"]
        networks = common.get_networks_for_instance(context, instance)
        return self._address_builder.index_view(networks)["addresses"]

    def _get_image(self, instance):
        image_ref = instance["image_ref"]
        image_id = str(common.get_id_from_href(image_ref))
        bookmark = self._image_builder._get_bookmark_link(image_id)
        return {
            "id": image_id,
            "links": [{
                "rel": "bookmark",
                "href": bookmark,
            }],
        }

    def _get_flavor(self, instance):
        flavor_id = instance["instance_type"]["flavorid"]
        flavor_ref = self._flavor_builder._get_href_link(flavor_id)
        flavor_bookmark = self._flavor_builder._get_bookmark_link(flavor_id)
        return {
            "id": str(common.get_id_from_href(flavor_ref)),
            "links": [{
                "rel": "bookmark",
                "href": flavor_bookmark,
            }],
        }
