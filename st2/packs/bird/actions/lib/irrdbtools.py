# Copyright (C) 2017 NL-ix
#               2017 Pier Carlo Chiodi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import ipaddr
import json
import subprocess

from .validators import ValidatorPrefixListEntry


def ensure_no_spaces(s):
    if s is None:
        return None
    return s.replace(' ', '')


class BGPQ3Error(Exception):
    pass


class BGPQ3Data(object):

    def __init__(self, bgpq3_path, bgpq3_host, bgpq3_sources, ip_ver):
        self.bgpq3_path = bgpq3_path
        self.bgpq3_host = bgpq3_host
        self.bgpq3_sources = bgpq3_sources
        if ip_ver in ["ipv4", "ipv6"]:
            self.ip_ver = ip_ver
        else:
            raise BGPQ3Error("Invalid IP version: {}".format(ip_ver))


class ASObjectPrefixes(BGPQ3Data):
    def __init__(self, bgpq3_path, bgpq3_host,
                 bgpq3_sources, ip_ver, as_object):
        super(ASObjectPrefixes, self).__init__(bgpq3_path, bgpq3_host,
                                               bgpq3_sources, ip_ver)

        self.as_object = as_object
        self.data = self._get_data()

    def _get_data(self):
        bgpq3_sources = ensure_no_spaces(self.bgpq3_sources)

        cmd = [self.bgpq3_path]
        cmd += ["-h", self.bgpq3_host]
        cmd += ["-S", bgpq3_sources]
        cmd += ["-3"]
        cmd += ["-6"] if self.ip_ver == "ipv6" else ["-4"]
        cmd += ["-A"]
        cmd += ["-j"]
        cmd += ["-l", "prefix_list"]
        cmd += [self.as_object]

        try:
            out = subprocess.check_output(cmd)
        except Exception as e:
            raise BGPQ3Error(
                "Can't get authorized prefix list for {} IPv{}: {}".format(
                    self.as_object, self.ip_ver, str(e))
            )

        try:
            data = json.loads(out)
        except Exception as e:
            raise BGPQ3Error(
                "Error while parsing bgpq3 output "
                "for the following command: '{}': {}".format(
                    " ".join(cmd), str(e)
                )
            )

        return [self._parse_prefix(prefix) for prefix in data["prefix_list"]]

    def _parse_prefix(self, raw):
        prefix = ipaddr.IPNetwork(raw["prefix"])
        res = {
            "prefix": str(prefix.ip),
            "length": prefix.prefixlen,
            "exact": raw["exact"] if "exact" in raw else False,
            "comment": self.as_object
        }
        if res["exact"]:
            res["ge"] = None
            res["le"] = None
        else:
            if "greater-equal" in raw:
                res["ge"] = raw["greater-equal"]
            else:
                res["ge"] = None

            if "less-equal" in raw:
                res["le"] = raw["less-equal"]
            else:
                res["le"] = None

        return ValidatorPrefixListEntry().validate(res)
