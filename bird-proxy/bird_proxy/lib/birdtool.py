# Copyright (c) 2017 NL-ix
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

import errno
import re
import os

from werkzeug.utils import secure_filename

from bird_proxy.lib import bird


class BIRDToolError(Exception):
    pass


class MissingCommandArgument(Exception):
    pass


class BIRDCommand(object):

    ALLOW_EMPTY_LINES = False

    def __init__(self, bird_connection):
        self.bird_connection = bird_connection

    def parse_result(self, result):
        return result

    def execute(self, **kwargs):
        try:
            command = self.COMMAND_TEMPLATE.format(**kwargs)

        except KeyError as e:
            raise MissingCommandArgument("argument {} not specified".format(e))

        result = self.bird_connection.cmd(
            command,
            allow_empty_lines=self.ALLOW_EMPTY_LINES)

        return self.parse_result(result)


class ValidateConfigCommand(BIRDCommand):
    COMMAND_TEMPLATE = 'configure check "{config_filename}"'


class ConfigureCommand(BIRDCommand):
    COMMAND_TEMPLATE = 'configure "{config_filename}"'


class ProtocolInformationCommand(BIRDCommand):
    COMMAND_TEMPLATE = 'show protocols all {wildcard}'

    ALLOW_EMPTY_LINES = True

    def parse_result(self, data):
        success, lines = data

        if not success:
            return success, lines

        results = []
        current_result = None

        for line in lines.splitlines():
            # an empty line indicates the end of the previous result
            if line == '':
                if current_result is not None:
                    results.append(current_result)

                current_result = None
                continue

            new_peer = re.match(r'^\s*(?P<session_name>peer_[^ ]+)', line)
            if new_peer is not None:
                current_result = {
                    'session_name': new_peer.group('session_name'),
                    'description': None,
                    'ip_address': None,
                    'as_number': None,
                    'prefixes': {
                        'imported': 0,
                        'exported': 0,
                        'preferred': 0,
                    },
                }
                continue

            if current_result is None:
                # we cannot continue processing if we didn't find a peer to process
                continue

            description = re.match(r'^\s*Description:\s+(?P<description>.*)$', line)
            if description is not None:
                current_result['description'] = description.group('description')

            routes = re.match(
                r'^\s*Routes:\s+'
                '(?P<imported>\d+) imported, '
                '(?P<exported>\d+), '
                '(?P<preferred>\d+) preferred$', line)
            if routes is not None:
                current_result['prefixes'] = {
                    'imported': routes.group('imported'),
                    'exported': routes.group('exported'),
                    'preferred': routes.group('preferred'),
                }

            bgp_state = re.match(r'^\s*BGP state:\s+(?P<bgp_state>\w+)$', line)
            if bgp_state is not None:
                current_result['bgp_state'] = bgp_state.group('bgp_state')

            ip_address = re.match(
                r'^\s*Neighbor address:\s+'
                '(?P<ip_address>\d+\.\d+\.\d+\.\d+)$', line)
            if ip_address is not None:
                current_result['ip_address'] = ip_address.group('ip_address')

            as_number = re.match(r'^\s*Neighbor AS:\s+(?P<as_number>\d+)$', line)
            if as_number is not None:
                current_result['as_number'] = int(as_number.group('as_number'))

        return True, results


class BIRDManager(object):

    def __init__(self, ip_version, bird_proxy_config):

        if ip_version == 'ipv4':
            self.bird_socket_file = bird_proxy_config["BIRD_SOCKET"]

        elif ip_version == 'ipv6':
            self.bird_socket_file = bird_proxy_config["BIRD6_SOCKET"]

        else:
            raise BIRDToolError("Invalid IP version: {}".format(ip_version))

        self.ip_version = ip_version
        self.base_config_folder = bird_proxy_config.get("BIRD_CONFIG_FOLDER")

    def connect(self):
        return bird.BirdSocket(file=self.bird_socket_file)

    def store_config_file(self, bird_config_file):
        bird_config_filename = os.path.join(
            self.base_config_folder,
            secure_filename(bird_config_file.filename))

        try:
            bird_config_file.save(bird_config_filename)
        except IOError as e:
            raise BIRDToolError("Unable to save config file: {}".format(e))

        return bird_config_filename

    def deploy_config(self, bird_config_file):

        bird_config_filename = self.store_config_file(bird_config_file)
        conn = self.connect()
        validation_out = ValidateConfigCommand(conn).execute(
            config_filename=bird_config_filename)
        if validation_out[0] is not True:
            os.remove(bird_config_filename)
            return validation_out

        configure_out = ConfigureCommand(conn).execute(
            config_filename=bird_config_filename)

        # create symlink to the latest config file to keep track of what file
        # ought to be used as the current bird configuration file
        # note that this step must only take place if configuration went
        # succesfully
        if configure_out[0] is True:
            self.symlink_latest_config_file(bird_config_filename)

        return configure_out

    def symlink_latest_config_file(self, bird_config_filename):
        latest_filename = 'bird-{}-latest.conf'.format(self.ip_version)
        latest_bird_config_path = os.path.join(self.base_config_folder,
                                               latest_filename)

        try:
            os.symlink(bird_config_filename, latest_bird_config_path)

        except OSError as e:
            if e.errno == errno.EEXIST:
                # the symlink already exists; remove it before creating it
                # (os.symlink does not support force)
                os.remove(latest_bird_config_path)
                os.symlink(bird_config_filename, latest_bird_config_path)

            else:
                raise

    def get_protocol_information_verbose(self, wildcard=None):
        conn = self.connect()

        if wildcard is None:
            wildcard = ''

        command = ProtocolInformationCommand(conn)
        result = command.execute(wildcard=wildcard)

        return result
