#!/usr/bin/env python3

import json  # noqa
import time  # noqa
import argparse
import asyncio
import signal
import collections
import logging
import sys

from mfba.network import (    
    Message,
    Node,
)
from mfba.common import (
    log,
)
from mfba.blockchain import (
    Blockchain,
)


NodeConfig = collections.namedtuple(
    'NodeConfig',
    (
        'name',
        'endpoint',
        'threshold',
    ),
)


def cancel_task_handler():    
    for task in asyncio.Task.all_tasks():
        task.cancel()    
    sys.exit(1)

def check_threshold(v):
    v = int(v)
    if v < 1 or v > 100:
        raise argparse.ArgumentTypeError(
            '%d is an invalid thresdhold, it must be 0 < trs <= 100' % v,
        )

    return v


parser = argparse.ArgumentParser()
parser.add_argument('-s', dest='silent', action='store_true', help='turn off the debug messages')
parser.add_argument('-nodes', type=int, default=4, help='number of validator nodes in the same quorum; default 4')
parser.add_argument('-trs', type=check_threshold, default=80, help='threshold; 0 < trs <= 100')


if __name__ == '__main__':
    log_level = logging.DEBUG
    if '-s' in sys.argv[1:]:
        log_level = logging.INFO

    log.set_level(log_level)

    options = parser.parse_args()
    log.main.debug('options: %s', options)

    client0_config = NodeConfig('client0', None, None)
    client0_node = Node(client0_config.name, client0_config.endpoint, None)
    log.main.debug('client node created: %s', client0_node)
    client1_config = NodeConfig('client1', None, None)
    client1_node = Node(client1_config.name, client1_config.endpoint, None)
    log.main.debug('client node created: %s', client1_node)

    nodes_config = dict()
    validators_config = dict()
    for i in range(options.nodes):
        name = 'n%d' % i
        endpoint = 'sock://memory:%d' % i
        nodes_config[name] = NodeConfig(name, endpoint, options.trs)

    for name, config in nodes_config.items():
        validators_config[name] = filter(lambda x: x.name != name, nodes_config.values())

    log.main.debug('node configs created: %s', nodes_config)
    log.main.debug('validator configs created: %s', validators_config)    

    # multi blockchain, each blockchain belongs to a quorum, we can add, remove as well as add, remove nodes in quorum
    blockchains = dict()

    loop = asyncio.get_event_loop()
    # add handler when receive stop signal
    loop.add_signal_handler(signal.SIGINT, cancel_task_handler)

    # these blockchains can be add and remove as well as nodes inside quorum
    for name, node_config in nodes_config.items():        
        blockchains[name] = Blockchain(node_config, validators_config[name], loop)        
        blockchains[name].start()
        
    # send message to `server0`    
    blockchains['n0'].send(client0_node)    

    try:
        loop.run_forever()        
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        log.main.debug('Tasks has been canceled')
    finally:
        loop.close()
        log.main.info('goodbye~')