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
import os

from st2actions.runners.pythonrunner import Action
from st2client.client import Client

from lib.configlib import BIRDConfigIPv4, BIRDConfigIPv6, BirdConfigLibError


class GenerateConfig(Action):

    def run(self, router_id, ip_version,
            peers_data=[], peers_data_datastore_key=None):

        try:
            config_data = self.config['bird_servers'][router_id]
        except KeyError:
            return (False, "Unknown router {}".format(router_id))

        if peers_data_datastore_key and not peers_data:

            api_base_url = self.config.get('st2_base_url')
            st_client = Client(base_url=api_base_url)

            try:
                peers_data = json.loads(st_client.keys.get_by_name(name=peers_data_datastore_key).value)
            except ValueError as e:
                return (False, "Error in peers data deconding: {}".format(e))
            except AttributeError as e:
                return (False, "Invalid datastore key: {}".format(e))

        # TODO Add a peers_data validator

        if ip_version == 'ipv4':
            template_file = config_data.get('ipv4_config_template')
            context_values = config_data.get('ipv4_config_context_values')
            birdconfig_class = BIRDConfigIPv4
        elif ip_version == 'ipv6':
            template_file = config_data.get('ipv6_config_template')
            context_values = config_data.get('ipv6_config_context_values')
            birdconfig_class = BIRDConfigIPv6
        else:
            return (False, "Invalid IP version {}".format(ip_version))

        peering_network = config_data['peering_network']

        outdir = os.path.join(self.config['config_storage_basedir'],
                              router_id,
                              ip_version)

        try:
            config = birdconfig_class(api_base_url, ip_version,
                                      peering_network, template_file,
                                      context_values)
            conf_content = config.generate_config_content(peers_data)
            conf_file = config.store_config(conf_content, outdir)
        except BirdConfigLibError as e:
            return (False, str(e))

        return (True, conf_file)
