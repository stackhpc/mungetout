#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Converts Openstack Ironic introspection data to a format accepted
by cardiff from python hardware.
"""
from __future__ import division, print_function, absolute_import

import argparse
import logging
import json
import sys
import re

from mungetout import __version__

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"

_logger = logging.getLogger(__name__)


_field_blacklist = [
    # (u'hpa', u'slot_0', u'total_cache_memory_available', u'0.3')
    'total_cache_memory_available',
    # Strip out serial numbers e.g from ssacli for HP servers:
    #  (u'disk', u'1I:1:2', u'wwid', u'1234567'),
    'wwid'
]


def _parse_cmdline_param(p):
    # given ipa-collect-lldp=1, produce: ('ipa-collect-lldp', '1')
    # given nofb, produce: ('nofb', None)
    key_values = tuple(p.split("=", 1))
    return key_values if len(key_values) > 1 else (key_values[0], None)


def _cmdline2dict(cmdline):
    # given "ipa-collect-lldp=1", produce: {"ipa-collect-lldp": "1"}
    split_on_ws = cmdline.split()
    mapping = dict([_parse_cmdline_param(p) for p in split_on_ws])
    return mapping


def _dict2cmdline(mappings):
    # given "{"ipa-collect-lldp": "1"}", produce: "ipa-collect-lldp=1"
    # given ('nofb', None), produce nofb
    items = []
    for key, value in mappings.items():
        if value:
            items.append("{key}={value}".format(key=key, value=value))
        else:
            items.append(key)
    return " ".join(items)


def _use_placeholder(cmdline_dict, key):
    if key in cmdline_dict:
        logging.debug("Using placeholder for key: {}".format(key))
        cmdline_dict[key] = "PLACEHOLDER"


def _clean_kernel_cmdline(item):
    # ('system', 'kernel', 'cmdline',
    # 'ipa-inspection-callback-url=http://10.64.0.10:5050/v1/continue systemd.journald.forward_to_console=yes \ # noqa
    # ip=10.64.0.231:10.64.0.10:10.64.0.10:255.255.254.0 BOOTIF=80:c1:6e:7a:73:98 \  # noqa
    # nofb nomodeset vga=normal console=ttyS0 ipa-collect-lldp=1 \
    # ipa-inspection-collectors=default,logs,pci-devices,extra-hardware \
    # ipa-inspection-benchmarks=cpu,disk,mem')
    if len(item) < 4 or item[0] != "system" or item[1] != "kernel" or \
            item[2] != "cmdline":
        return item
    logging.debug("Before _clean_kernel_cmdline: {}".format(item[3]))
    cmdline = _cmdline2dict(item[3])
    # Remove unique values that prevent systems from being grouped
    _use_placeholder(cmdline, "BOOTIF")
    _use_placeholder(cmdline, "ip")
    cleaned = _dict2cmdline(cmdline)
    logging.debug("After _clean_kernel_cmdline: {}".format(cleaned))
    return cleaned


def _clean_temperatures(item):
    # Strip out temperatures e.g from ssacli for HP servers:
    # (u'disk', u'1I:1:2', u'maximum_temperature_c', u'27'),
    # (u'disk', u'1I:1:2', u'current_temperature_c', u'18'),
    # (u'hpa', u'slot_0', u'capacitor_temperature_c', u'12'),
    if len(item) < 4 or "temperature" not in item[2]:
        return item
    logging.debug("_clean_temperatures, removing: {}".format(item))
    return None


def _clean_boot_volume(item):
    # (u'hpa',
    #  u'slot_0',
    #  u'secondary_boot_volume',
    #  u'logicaldrive 1 (600508B1001C6D568C431707B847FA3A)'),
    if len(item) < 4 or item[2] not in \
            ["primary_boot_volume", "secondary_boot_volume"]:
        return item
    # Only keep "logicaldrive NUM" component
    match = re.search("^(logicaldrive [0-9]+) \(.*?\)", item[3])
    if not match:
        return item
    return item[0], item[1], item[2], match.group(1)


def _clean_generic_field(item):
    if len(item) < 4 or item[2] not in _field_blacklist:
        return item
    logging.debug("_clean_generic field removing: {}".format(item))
    return None


def _modify(item):
    steps = [
        _clean_kernel_cmdline,
        _clean_temperatures,
        _clean_generic_field
    ]
    for step in steps:
        item = step(item)
        # A step may return None to remove the value
        if not item:
            break
    return item


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Munges OpenStack Ironic introspection data to "
                    "a format accepted by cardiff")
    parser.add_argument(
        '--version',
        action='version',
        version='mungetout {ver}'.format(ver=__version__))
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


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stderr,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    data = json.load(sys.stdin)
    # modify then strip falsy values
    tuples = filter(lambda x: x, [_modify(tuple(xs)) for xs in data])
    print(list(tuples))


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
