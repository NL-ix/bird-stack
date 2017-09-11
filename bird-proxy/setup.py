#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import bird_proxy

setup(
    name='bird-proxy',
    version=bird_proxy.__version__,
    description='Web API to communicate with BIRD',
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    include_package_data=True,
    zip_safe=False,
)
