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

import os.path


from nova.api.openstack import common


class ViewBuilder(common.ViewBuilder):

    _resource_name = "flavors"

    def basic_view(self, flavor):
        return {
            "flavor": {
                "id": flavor["flavorid"],
                "name": flavor["name"],
                "links": self._get_links(flavor["flavorid"]),
            },
        }

    def show_view(self, flavor):
        return {
            "flavor": {
                "id": flavor["flavorid"],
                "name": flavor["name"],
                "ram": flavor["memory_mb"],
                "disk": flavor["local_gb"],
                "vcpus": flavor.get("vcpus") or "",
                "swap": flavor.get("swap") or "",
                "rxtx_quota": flavor.get("rxtx_quota") or "",
                "rxtx_cap": flavor.get("rxtx_cap") or "",
                "links": self._get_links(flavor["flavorid"]),
            },
        }

    def index_view(self, flavors):
        items = flavors.iteritems()
        flavors = [self.basic_view(flavor)["flavor"] for _, flavor in items]
        return dict(flavors=flavors)

    def detail_view(self, flavors):
        items = flavors.iteritems()
        flavors = [self.show_view(flavor)["flavor"] for _, flavor in items]
        return dict(flavors=flavors)
