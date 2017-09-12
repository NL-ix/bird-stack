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
import os
import re
import yaml


class ConfigError(Exception):
    pass


def validate_application_name(name):
    PATTERN = '\A[a-zA-Z0-9_-]+\Z'
    return re.match(PATTERN, name) is not None


def get_config_base_path():
    return os.environ.get('BIRD_PROXY_CONFIG_BASE_PATH', '/')


def build_config_path(application_name):
    base_path = get_config_base_path() or '/'
    application_path = os.path.join('etc', os.path.basename(application_name))

    return os.path.join(base_path, application_path)


def get_config(application_name):
    if not isinstance(application_name, str):
        raise TypeError("invalid config name")

    if not validate_application_name(application_name):
        raise ValueError("invalid application name")

    config_dict = {}
    config_path = build_config_path(application_name)
    config_filename = application_name + '.yaml'

    def get_filepath(defaults=False):
        default_path = 'defaults' if defaults else ''
        return os.path.join(
            config_path,
            default_path,
            os.path.basename(config_filename))

    # Load default config
    default_filename = get_filepath(defaults=True)
    default_config = get_dict_from_yaml_file(default_filename)

    config_dict.update(default_config)

    # Load specific config to override defaults
    override_filename = get_filepath()
    override_config = get_dict_from_yaml_file(override_filename)

    config_dict.update(override_config)

    return config_dict


def get_dict_from_yaml_file(filename):
    try:
        with open(filename) as config_file:
            contents = config_file.read()
            config = yaml.load(contents)

            if config is None:
                return {}

            return config

    except (OSError, IOError) as e:
        if e.errno == errno.ENOENT:
            raise ConfigError("Config file `{}` does not exist".format(filename))

        if e.errno == errno.EACCES:
            raise ConfigError("No permission to read config file `{}`".format(filename))

        raise

    except yaml.YAMLError:
        raise ConfigError("Config file contains invalid content")
