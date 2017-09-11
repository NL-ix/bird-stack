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

from st2actions.runners.pythonrunner import Action

from lib.birdproxy import BIRDProxyError, DeployConfigFileRequest


class DeployConfig(Action):

    def run(self, router_id, ip_version, config_file):

        try:
            config = self.config['bird_servers'][router_id]
        except KeyError:
            return (False, "Route server {} unknown".format(router_id))

        dest_host = config.get('host')
        listen_web_port = config.get('listen_web_port')
        api_token = config.get('api_token')

        try:
            resp = DeployConfigFileRequest(dest_host, listen_web_port,
                                           api_token, config_file,
                                           ip_version).execute()
        except BIRDProxyError as e:
            return (False, str(e))
        return (bool(resp.get("outcome")), resp.get("message"))
