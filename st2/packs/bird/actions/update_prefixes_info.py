# Copyright (C) 2017 NL-ix
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

import json

from st2actions.runners.pythonrunner import Action
from st2client.client import Client
from st2client.models import KeyValuePair

from lib.irrdbtools import ASObjectPrefixes, BGPQ3Error


class UpdatePrefixesInfo(Action):

    def run(self, as_objects, ip_version, timeout=None):

        BGPQ3_DEFAULT_HOST = "rr.ntt.net"
        BGPQ3_DEFAULT_SOURCES = ("RIPE,APNIC,AFRINIC,ARIN,NTTCOM,ALTDB,"
                                 "BBOI,BELL,GT,JPIRR,LEVEL3,RADB,RGNET,"
                                 "SAVVIS,TC")

        bgpq3_path = self.config.get("bgpq3_path", "bgpq3")
        bgpq3_host = self.config.get("bgpq3_host", BGPQ3_DEFAULT_HOST)
        bgpq3_sources = self.config.get("bgpq3_sources", BGPQ3_DEFAULT_SOURCES)

        api_base_url = self.config.get('st2_base_url')
        st_client = Client(base_url=api_base_url)

        as_objects_count = len(as_objects)
        updates_count = 0

        for as_set in as_objects:
            try:
                prefixes = ASObjectPrefixes(bgpq3_path, bgpq3_host,
                                            bgpq3_sources, ip_version,
                                            as_set).data
            except BGPQ3Error as e:
                self.logger.error("{}".format(e))
                continue
            as_set_key = "prefixes_{}_{}".format(as_set, ip_version)
            as_set_value = ["{}/{}".format(p["prefix"], p["length"])
                            for p in prefixes]
            as_set_prefixes_pair = KeyValuePair(name=as_set_key,
                                                value=json.dumps(as_set_value))
            try:
                st_client.keys.update(as_set_prefixes_pair)
            except Exception as e:
                self.logger.error("{}".format(e))
                continue
            updates_count += 1

        if updates_count != as_objects_count:
            return (False, "Incomplete update: {}/{}".format(updates_count,
                                                             as_objects_count))
        else:
            return (True, "{}/{} as-objects info updated".format(updates_count,
                                                                 as_objects_count))
