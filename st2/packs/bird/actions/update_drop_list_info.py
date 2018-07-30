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
import requests

from st2common.runners.base_action import Action
from st2client.client import Client
from st2client.models import KeyValuePair


class UpdateDropListInfo(Action):

    def run(self, ip_version):

        if ip_version == 'ipv4':
            urls = self.config.get('ipv4_drop_list_source_urls')
        elif ip_version == 'ipv6':
            urls = self.config.get('ipv6_drop_list_source_urls')
        else:
            return (False, 'Invalid ip version {}'.format(ip_version))

        ret = []

        for url in urls:
            try:
                r = requests.get(url)
            except requests.exceptions.RequestException as e:
                return (False, str(e))

            request_out = r.text

            # TODO Implement a generic parsing algorithm
            drop_list = [p.split(";")[0].strip()
                         for p in request_out.split("\n")[4:-1]]
            ret += drop_list

        api_base_url = self.config.get('st2_base_url')
        st_client = Client(base_url=api_base_url)
        drop_list_key = "drop_list_prefixes_{}".format(ip_version)
        drop_list_value = json.dumps(list(set(ret)))
        drop_list_pair = KeyValuePair(name=drop_list_key,
                                      value=drop_list_value)
        try:
            st_client.keys.update(drop_list_pair)
        except Exception as e:
            return (False, str(e))

        return (True, drop_list_key)
