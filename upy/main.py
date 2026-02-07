#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2025-11-16
# modified: 2026-02-07

# configuration for TinyS3
I2C_ID      = 0
I2C_ADDRESS = 0x47
SCL_PIN     = 7
SDA_PIN     = 6

RELOAD      = True

import sys
import time
import asyncio

from i2c_slave import I2CSlave
from controller import Controller

if RELOAD:
    import gc
    # force module reload
    for mod in ['main', 'i2c_slave', 'controller']:
        if mod in sys.modules:
            del sys.modules[mod]
    gc.collect()

async def i2c_loop(controller, slave):
    global enabled
    _last_time = time.ticks_ms()
    while enabled:
        _current_time = time.ticks_ms()
        controller.tick(time.ticks_diff(_current_time, _last_time))
        slave.check_and_process()
        _last_time = _current_time
        await asyncio.sleep_ms(1)

def start():
    global enabled

    enabled = True
    slave   = None

    try:

        controller = Controller()
        slave = I2CSlave(i2c_id=I2C_ID, scl=SCL_PIN, sda=SDA_PIN, i2c_address=I2C_ADDRESS)
        slave.add_callback(controller.process)
        controller.set_slave(slave)
        slave.enable()
        # run event loop
        asyncio.run(i2c_loop(controller, slave))

    except KeyboardInterrupt:
        print('\nCtrl-C caught; exiting…')
    except Exception as e:
        print('ERROR: {} raised in start: {}'.format(type(e), e))
        sys.print_exception(e)
    finally:
        enabled = False
        print('complete.')

#if __name__ == "__main__":
start()

#EOF
