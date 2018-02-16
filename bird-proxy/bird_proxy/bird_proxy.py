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

import functools
import sys
import traceback

from flask import Flask, request, jsonify
from lib import birdtool, config

app = Flask(__name__)

APPLICATION_NAME = 'bird-proxy'

# Load our file-based config file
try:
    CONFIG = config.get_config(APPLICATION_NAME)

except config.ConfigError as e:
    print >> sys.stderr, "Failed to load config:"
    print >> sys.stderr, e
    sys.exit(1)

app.config.from_mapping(CONFIG)


def token_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        api_token = request.form.get('api_token')

        if api_token != app.config['API_TOKEN']:
            app.logger.debug("Token validation failed")
            data = {
                'message': "Invalid API token supplied",
                'outcome': False
            }

            return jsonify(data), 401
        return f(*args, **kwargs)
    return wrapped


@app.route("/deployconfig", methods=["POST"])
@token_required
def bird_deployconfig():
    # Config file retrieval

    try:
        config_file = request.files['file']
    except KeyError:
        app.logger.error("{}".format(traceback.format_exc()))
        data = {"message": "Config file not provided", "outcome": False}
        return jsonify(data), 400

    # File Deployment

    ip_version = request.form.get('ip_version')

    try:
        bird = birdtool.BIRDManager(ip_version, app.config)
        config_out = bird.deploy_config(config_file)
        return jsonify({"message": config_out[1], "outcome": config_out[0]})
    except birdtool.BIRDToolError as e:
        app.logger.error("{}".format(traceback.format_exc()))
        return jsonify({"message": str(e), "outcome": False})


@app.route('/protocol/info/verbose', methods=['POST'])
@token_required
def protocol_info_verbose():
    outcome = False

    ip_version = request.form.get('ip_version')

    # TODO allow wildcard to be specified
    wildcard = '"peer_*"'

    try:
        bird = birdtool.BIRDManager(ip_version, app.config)
        outcome, message = bird.get_protocol_information_verbose(wildcard=wildcard)

    except birdtool.BIRDToolError as e:
        app.logger.exception("failed to retrieve data from bird")

        message = str(e)

    return jsonify({
        'outcome': outcome,
        'message': message
    })


@app.route('/routesinfo', methods=['POST'])
@token_required
def routes_info():
    outcome = False

    ip_version = request.form.get('ip_version')

    forwarding_table = request.form.get('forwarding_table')
    prefix = request.form.get('prefix')
    table = request.form.get('table')
    fltr = request.form.get('fltr')
    where = request.form.get('where')
    detail = request.form.get('detail')
    export_mode = request.form.get('export_mode')
    export_protocol = request.form.get('export_protocol')
    protocol = request.form.get('protocol')

    try:
        bird = birdtool.BIRDManager(ip_version, app.config)
        outcome, message = bird.get_routes_information(
            forwarding_table=forwarding_table, prefix=prefix, table=table,
            fltr=fltr, where=where, detail=detail,
            export_mode=export_mode, export_protocol=export_protocol,
            protocol=protocol)

    except birdtool.BIRDToolError as e:
        app.logger.exception("failed to retrieve data from bird")

        message = str(e)

    return jsonify({
        'outcome': outcome,
        'message': message
    })
