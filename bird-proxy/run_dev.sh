#!/bin/bash

export BIRD_PROXY_CONFIG_BASE_PATH="/home/$(whoami)/bird-proxy-data"
export FLASK_APP=bird_proxy/bird_proxy.py

source env/bin/activate

PORT="${1:-8005}"

flask run --port="${PORT}"
