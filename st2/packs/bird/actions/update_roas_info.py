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
import ipaddr
import requests

from st2common.runners.base_action import Action
from st2client.client import Client
from st2client.models import KeyValuePair

from lib.validators import ValidatorROA, ValidationError


class UpdateROAsInfo(Action):

    def run(self):
        source_urls = self.config.get('roas_info_source_urls')
        rir_trust_anchors = self.config.get('rir_trust_anchors')

        ret = []

        for url in source_urls:
            try:
                r = requests.get(url)
            except requests.exceptions.RequestException as e:
                return (False, str(e))

            request_out = r.json().get("roas", [])
            trusted_entries = filter(
                lambda x: x['ta'] in rir_trust_anchors, request_out)

            roas_info = []
            for roa in trusted_entries:

                if roa.get('asn').startswith("AS"):
                    asn = int(roa.get('asn')[2:])
                else:
                    asn = int(roa.get('asn'))

                prefix = ipaddr.IPNetwork(roa.get('prefix'))
                prefix_obj = {
                    "prefix": str(prefix.ip),
                    "length": int(prefix.prefixlen),
                    "max_length": int(roa.get('maxLength'))
                }
                try:
                    validated_roa_entry = ValidatorROA().validate(
                        {'asn': asn, 'prefix': prefix_obj})
                except ValidationError:
                    continue

                roas_info.append(validated_roa_entry)
            ret += roas_info

        api_base_url = self.config.get('st2_base_url')
        st_client = Client(base_url=api_base_url)

        roas_info_keys = []
        for ip_version in [4, 6]:
            roas_key = "roas_info_ipv{}".format(ip_version)
            roas_info_keys.append(roas_key)
            ipv_roas_info = filter(lambda x: x["prefix"]['version'] == ip_version, ret)
            roas_value = json.dumps([{'asn': roa['asn'],
                                      'prefix': "{}/{}".format(roa['prefix']['prefix'],
                                                               roa['prefix']['length']),
                                      'max_length': roa['prefix']['max_length']}
                                     for roa in ipv_roas_info])
            roas_info_pair = KeyValuePair(name=roas_key,
                                          value=roas_value)
            try:
                st_client.keys.update(roas_info_pair)
            except Exception as e:
                return (False, str(e))

        return (True, roas_info_keys)
