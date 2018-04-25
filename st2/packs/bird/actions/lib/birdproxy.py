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

import requests


class BIRDProxyError(Exception):
    pass


class BIRDProxyRequest(object):

    def __init__(self, dest_host, listen_web_port, api_token):
        if listen_web_port:
            self.base_url = "{}:{}".format(dest_host,
                                           listen_web_port)
        else:
            self.base_url = "{}".format(dest_host)

        self.api_token = api_token

    def execute(self):
        raise NotImplementedError()

    def _parse_response(self, response):
        try:
            resp_data = response.json()
        except requests.exceptions.RequestException as e:
            raise BIRDProxyError(str(e))
        except ValueError as e:
            raise BIRDProxyError("Bad bird-proxy response: {}".format(e))

        return resp_data


class DeployConfigFileRequest(BIRDProxyRequest):

    def __init__(
            self, dest_host, listen_web_port, api_token,
            config_file, ip_version):
        super(DeployConfigFileRequest, self).__init__(dest_host,
                                                      listen_web_port,
                                                      api_token)

        self.config_file = config_file
        self.ip_version = ip_version
        self.url = "deployconfig"

    def execute(self):
        try:
            files = {'file': open(self.config_file, 'rb')}
        except IOError as e:
            raise BIRDProxyError(
                "Error in the BIRD config file retrival: {}".format(e))

        data = {
            'api_token': self.api_token,
            'ip_version': self.ip_version
        }

        url = "{}/{}".format(self.base_url, self.url)
        try:
            r = requests.post(url, files=files, data=data)
        except Exception as e:
            raise BIRDProxyError(
                "Error in the BIRD config file deployment: {}".format(e))

        return self._parse_response(r)


class SessionsInfoRequest(BIRDProxyRequest):

    def __init__(self, dest_host, listen_web_port, api_token, ip_version):
        super(SessionsInfoRequest, self).__init__(dest_host,
                                                  listen_web_port,
                                                  api_token)

        self.ip_version = ip_version
        self.url = 'protocol/info/verbose'

    def execute(self):

        data = {
            'api_token': self.api_token,
            'ip_version': self.ip_version
        }

        url = "{}/{}".format(self.base_url, self.url)
        try:
            r = requests.post(url, data=data)
        except Exception as e:
            raise BIRDProxyError(
                "Error in the BIRD sessions info retrieval: {}".format(e))

        return self._parse_response(r)


class RoutesInfoRequest(BIRDProxyRequest):

    def __init__(self, dest_host, listen_web_port,
                 api_token, ip_version, command_parameters):
        super(RoutesInfoRequest, self).__init__(dest_host,
                                                listen_web_port,
                                                api_token)

        self.ip_version = ip_version
        self.url = 'routesinfo'
        self.command_parameters = command_parameters

    def execute(self):

        data = {
            'api_token': self.api_token,
            'ip_version': self.ip_version
        }

        data.update(self.command_parameters)

        url = "{}/{}".format(self.base_url, self.url)
        try:
            r = requests.post(url, data=data)
        except Exception as e:
            raise BIRDProxyError(
                "Error in the BIRD routes info retrieval: {}".format(e))

        return self._parse_response(r)
