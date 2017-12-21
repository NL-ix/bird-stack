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

import os
import json
import jinja2
from datetime import datetime
from operator import itemgetter

from st2client.client import Client


def us_ipv4(ipv4_ip):
    return ipv4_ip.replace(".", "_")


def us_ipv6(ipv6_ip):
    return ipv6_ip.replace(":", "_")


def int_ipv4(ipv4_address, network):
    octets = ipv4_address.split(".")
    diff = int(network.split(".")[2])
    o3 = str(int(octets[2]) - diff)
    o4 = str(octets[3])
    if len(o4) < 3:
        o4 = ("0" * (3 - len(o4))) + o4
    return o3 + o4


class BirdConfigLibError(Exception):
    pass


class BIRDConfig(object):

    def __init__(
            self, st2_api_base_url, ip_version, peering_network,
            config_template, context_data):
        self.st_client = Client(base_url=st2_api_base_url)
        self.ip_version = ip_version
        self.peering_network = peering_network
        self.config_template_file = config_template
        self.context_data = context_data

    def _get_fullbogons(self):
        fullbogons_key = "fullbogons_{}".format(self.ip_version)
        try:
            fullbogons = json.loads(self.st_client.keys.get_by_name(name=fullbogons_key).value)
        except ValueError as e:
            raise BirdConfigLibError("Error in stored bogons deconding: {}".format(e))
        except AttributeError as e:
            raise BirdConfigLibError("NO fullbogons stored in the system.({})".format(e))
        return fullbogons

    def _get_drop_list_prefixes(self):
        drop_list_key = "drop_list_prefixes_{}".format(self.ip_version)
        try:
            drop_list_prefixes = json.loads(self.st_client.keys.get_by_name(name=drop_list_key).value)
        except ValueError as e:
            raise BirdConfigLibError("Error in stored DROP list info deconding: {}".format(e))
        except AttributeError as e:
            raise BirdConfigLibError("NO DROP list prefixes stored in the system.({})".format(e))
        return drop_list_prefixes


    def _get_roas_info(self):
        roas_info_key = "roas_info_{}".format(self.ip_version)
        try:
            roas_info = json.loads(self.st_client.keys.get_by_name(name=roas_info_key).value)
        except ValueError as e:
            raise BirdConfigLibError("Error in stored ROAs info decoding: {}".format(e))
        except AttributeError as e:
            raise BirdConfigLibError("NO ROAs info stored in the system.({})".format(e))
        return roas_info

    def get_prefixes(self, as_object):
        prefixes_key = "prefixes_{}_{}".format(as_object, self.ip_version)
        try:
            prefixes = json.loads(self.st_client.keys.get_by_name(name=prefixes_key).value)
        except ValueError as e:
            raise BirdConfigLibError("Error in stored prefixes deconding: {}".format(e))
        except AttributeError as e:
            prefixes = []
        return prefixes

    def _sort_sessions_data(self, peers_data):
        for peer in peers_data:
            for session in peer['sessions']:
                session['session_filter_int_ips'] = sorted(
                    session['session_filter_int_ips'])
                session['session_prepend_int_ips'] = sorted(
                    session['session_prepend_int_ips'])
            peer["sessions"] = sorted(
                peer['sessions'],
                key=itemgetter('session_ip'))
        return sorted(peers_data, key=itemgetter('peer_name'))

    def _format_peers_data(self):
        raise NotImplementedError()

    def generate_config_content(self, peers_data):

        env = jinja2.Environment(
            loader=jinja2.PackageLoader('lib', 'templates')
        )

        try:
            template_context_data = self.context_data
            template_context_data.update(
                {'peers_data': self._format_peers_data(peers_data),
                 'fullbogons': self._get_fullbogons(),
                 'drop_list_prefixes': self._get_drop_list_prefixes(),
                 'roas_info': self._get_roas_info()}
            )
        except Exception as e:
            raise BirdConfigLibError("Error in peers data formatting: {}".format(e))

        try:
            config_template = env.get_template(self.config_template_file)
            bird_config = config_template.render(template_context_data)
        except Exception as e:
            raise BirdConfigLibError("Error in the BIRD config generation: {}".format(e))

        return bird_config

    def store_config(self, config_content, outdir):
        try:
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            filename = "bird_{}_{}.conf".format(
                datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                self.ip_version)
            with open(os.path.join(outdir, filename), "w+") as outfile:
                outfile.write(config_content)
        except Exception as e:
            raise BirdConfigLibError("Error in the BIRD config saving: {}".format(e))

        self.config_filename = os.path.join(outdir, filename)

        return self.config_filename


class BIRDConfigIPv4(BIRDConfig):

    def _format_peers_data(self, peers_data):

        ret = {}

        for session in peers_data:
            peer_as = session['peer_as_number']
            peer_as_number = session['peer_as_number']
            peer_as_macro = session.get('peer_as_macro')

            if peer_as not in ret:

                if peer_as_macro:
                    as_object_key = peer_as_macro
                else:
                    if not peer_as_number.startswith("AS"):
                        as_object_key = "AS{}".format(peer_as_number)
                    else:
                        as_object_key = peer_as_number

                peer_data = {
                    'peer_name': session["peer_name"],
                    'peer_as_number': peer_as_number,
                    'peer_as_macro': peer_as_macro,
                    'prefixes': self.get_prefixes(as_object_key),
                    'sessions': []
                }
                ret.update({peer_as_number: peer_data})

            session = {
                'session_ip': session['ip_address']['ipv4'],
                'irrdb_filtering': session['cfg'].get('irrdb_filtering'),
                'roa_filtering': session['cfg'].get('roa_filtering'),
                'fullbogons_filtering': session['cfg'].get('fullbogons_filtering'),
                'drop_list_filtering': session['cfg'].get('drop_list_filtering'),
                'session_int_ip': int_ipv4(session['ip_address']['ipv4'],
                                           self.peering_network),
                'session_us_ip': us_ipv4(session['ip_address']['ipv4']),
                'session_bgp_password': session['cfg'].get('bgp_password'),
                'session_filter_ips': [ip['ipv4'] for ip in session['cfg'].get('filter_ips', [])],
                'session_prepend_ips': [ip['ipv4'] for ip in session['cfg'].get('prepend_ips', [])],
                'session_filter_int_ips': [int_ipv4(ip['ipv4'], self.peering_network)
                                           for ip in session['cfg'].get('filter_ips', [])],
                'session_prepend_int_ips': [int_ipv4(ip['ipv4'], self.peering_network)
                                            for ip in session['cfg'].get('prepend_ips', [])],
                'max_prefixes': session['cfg'].get('max_prefixes')
            }
            ret[peer_as]['sessions'].append(session)

        return self._sort_sessions_data(ret.values())


class BIRDConfigIPv6(BIRDConfig):

    def _ipv6_filter(self, ip_list):
        return filter(lambda x: x.get("ipv6"), ip_list)

    def _format_peers_data(self, peers_data):

        ret = {}

        ipv6_peers_data = filter(
            lambda x: x['ip_address'].get("ipv6"),
            peers_data)
        for session in ipv6_peers_data:
            peer_as = session['peer_as_number']
            peer_as_number = session['peer_as_number']
            peer_as_macro = session.get('peer_as_macro')

            if peer_as not in ret:

                if peer_as_macro:
                    as_object_key = peer_as_macro
                else:
                    if not peer_as_number.startswith("AS"):
                        as_object_key = "AS{}".format(peer_as_number)
                    else:
                        as_object_key = peer_as_number

                peer_data = {
                    'peer_name': session["peer_name"],
                    'peer_as_number': peer_as_number,
                    'peer_as_macro': peer_as_macro,
                    'prefixes': self.get_prefixes(as_object_key),
                    'sessions': []
                }
                ret.update({peer_as_number: peer_data})

            session = {
                'session_ip': session['ip_address']['ipv6'],
                'irrdb_filtering': session['cfg'].get('irrdb_filtering'),
                'roa_filtering': session['cfg'].get('roa_filtering'),
                'fullbogons_filtering': session['cfg'].get('fullbogons_filtering'),
                'drop_list_filtering': session['cfg'].get('drop_list_filtering'),
                'session_int_ip': int_ipv4(session['ip_address']['ipv4'],
                                           self.peering_network),
                'session_us_ip': us_ipv6(session['ip_address']['ipv6']),
                'session_bgp_password': session['cfg'].get('bgp_password'),
                'session_filter_ips': [ip['ipv6'] for ip in self._ipv6_filter(session['cfg'].get('filter_ips', []))],
                'session_prepend_ips': [ip['ipv6'] for ip in self._ipv6_filter(session['cfg'].get('prepend_ips', []))],
                'session_filter_int_ips': [int_ipv4(ip['ipv4'], self.peering_network)
                                           for ip in self._ipv6_filter(session['cfg'].get('filter_ips', []))],
                'session_prepend_int_ips': [int_ipv4(ip['ipv4'], self.peering_network)
                                            for ip in self._ipv6_filter(session['cfg'].get('prepend_ips', []))],
                'max_prefixes': session['cfg'].get('max_prefixes')
            }
            ret[peer_as]['sessions'].append(session)

        return self._sort_sessions_data(ret.values())
