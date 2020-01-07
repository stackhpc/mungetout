#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generates a directory tree containing extra hardware data suitable
for ingest by cardiff
"""
from __future__ import division, print_function, absolute_import

import argparse
import logging
import json
import subprocess
import sys
import os
import requests
import shlex
from subprocess import Popen, PIPE

from mungetout import __version__

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"

_logger = logging.getLogger(__name__)


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Generates extra hardware data in format "
                    "suitable for cardiff ingest from OpenStack "
                    "Ironic inspector")
    parser.add_argument(
        '--version',
        action='version',
        version='mungetout {ver}'.format(ver=__version__))
    parser.add_argument(
        '--inspection-store-url',
        dest='inspection_store',
        metavar="URL",
        nargs='?',
        default="http://localhost:8080/ironic-inspector",
        help="URL to download extra hardware data from")
    parser.add_argument(
        '--limit',
        dest='limit',
        metavar="MAX",
        nargs='?',
        type=int,
        help="Limit the number of nodes processed",
        default=None)
    parser.add_argument(
        '-v',
        '--verbose',
        dest="loglevel",
        help="set loglevel to INFO",
        action='store_const',
        const=logging.INFO)
    parser.add_argument(
        '-vv',
        '--very-verbose',
        dest="loglevel",
        help="set loglevel to DEBUG",
        action='store_const',
        const=logging.DEBUG)
    return parser.parse_args(args)


class DownloadException(Exception):
    pass


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stderr,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def _get_nodes():
    cmd = "openstack baremetal node list -f json -c UUID -c Name"
    output = subprocess.check_output(shlex.split(cmd))
    return json.loads(output)


def _get_introspection_data(uuid):
    cmd = "openstack baremetal introspection data save {}".format(uuid)
    output = subprocess.check_output(shlex.split(cmd))
    return json.loads(output)


def _get_extra_hardware_data(uuid, url):
    url = "{url}/extra_hardware-{node_uuid}".format(node_uuid=uuid, url=url)
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.HTTPError:
        raise DownloadException("Invalid status code")
    return response.json()


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    if args.limit:
        _logger.info("Using limit: {}".format(args.limit))
    skipped = 0
    i = 0
    nodes = _get_nodes()
    os.mkdir("results")
    for i, node in enumerate(nodes):
        if args.limit and i - skipped >= args.limit:
            skipped += len(nodes) - i
            break
        node_name = node["Name"]
        node_uuid = node["UUID"]

        if not node_name:
            _logger.warning("Node with uuid: {}, has no name. Skipping..."
                            .format(node_uuid))
            skipped += 1
            continue
        os.mkdir(node_name)

        introspection_data = _get_introspection_data(node_uuid)
        introspection_path = os.path.join(node_name, 'introspection_data.json')
        with open(introspection_path, 'w') as f:
            json.dump(introspection_data, f, indent=4, sort_keys=True)
        alt_path = os.path.join('results',
                                'introspection_data_{}'.format(node_name))
        os.symlink(os.path.join('..', introspection_path), alt_path)

        extra_data = _get_extra_hardware_data(node_uuid,
                                              url=args.inspection_store)
        extra_path = os.path.join(node_name, 'extra_hardware')
        with open(extra_path, 'w') as f:
            process = Popen(['cardiff-convert'], stdout=f, stdin=PIPE,
                            stderr=PIPE)
            process.communicate(input=json.dumps(extra_data))
        alt_path = os.path.join('results',
                                'extra_hardware_{}'.format(node_name))
        os.symlink(os.path.join('..', extra_path), alt_path)

    _logger.info("Processed {} nodes".format(i))
    _logger.info("Skipped {} nodes".format(skipped))


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])
