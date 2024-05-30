#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Komal Thareja (ktharej@renci.org)


class Metrics:
    def __init__(self, fablib_manager):
        self.fablib_manager = fablib_manager

    def list_metrics(
        self,
        output=None,
        fields=None,
        quiet=False,
        filter_function=None,
        pretty_names=True,
    ):
        table = []
        metric_dict = self.metrics_to_dict()
        table.append(metric_dict)

        if pretty_names:
            pretty_names_dict = self.pretty_names
        else:
            pretty_names_dict = {}

        return self.fablib_manager.list_table(
            table,
            fields=fields,
            title="Metrics",
            output=output,
            quiet=quiet,
            filter_function=filter_function,
            pretty_names_dict=pretty_names_dict,
        )

    def metrics_to_dict(self):
        """
        Convert Metrics information into a dictionary
        """
        site_info = self.get_site_info(site)
        d = {
            "name": site.name if isinstance(site, node.Node) else site.get_name(),
            "state": self.get_state(site),
            "address": self.get_location_postal(site),
            "location": self.get_location_lat_long(site) if latlon else "",
            "ptp_capable": self.get_ptp_capable(site),
            "hosts": self.get_host_capacity(site),
            "cpus": self.get_cpu_capacity(site),
        }

        for attribute, names in self.site_attribute_name_mappings.items():
            capacity = site_info.get(attribute, {}).get(self.CAPACITY.lower(), 0)
            allocated = site_info.get(attribute, {}).get(self.ALLOCATED.lower(), 0)
            available = capacity - allocated
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.AVAILABLE.lower()}"] = available
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.CAPACITY.lower()}"] = capacity
            d[f"{names.get(self.NON_PRETTY_NAME)}_{self.ALLOCATED.lower()}"] = allocated

        if not latlon:
            d.pop("location")

        return d
