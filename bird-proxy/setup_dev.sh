#!/bin/bash
# Set up the configuration file for a bird-proxy development environment

export BIRD_PROXY_CONFIG_BASE_PATH="/home/$(whoami)/bird-proxy-data"

/bin/mkdir -p "${BIRD_PROXY_CONFIG_BASE_PATH}/etc/bird-proxy/defaults"
cp debian/etc/bird-proxy/defaults/bird-proxy.yaml "${BIRD_PROXY_CONFIG_BASE_PATH}/etc/bird-proxy/defaults"
cp debian/etc/bird-proxy/defaults/bird-proxy.yaml "${BIRD_PROXY_CONFIG_BASE_PATH}/etc/bird-proxy"

/bin/mkdir -p "${BIRD_PROXY_CONFIG_BASE_PATH}/var/bird"

virtualenv env
source env/bin/activate
pip install -r requirements.txt
