#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2025-11-16
# modified: 2026-02-08
#
# I2C master controller, with CLI option to set I2C address. Permits repeat
# sending of a command using a worker thread loop initiated by "go" and halted
# by "stop".

import time
import argparse
from threading import Event, Lock, Thread

from i2c_master import I2CMaster

# ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

I2C_ID           = 1       # I2C bus identifier
I2C_ADDRESS      = 0x47    # I2C device address
WORKER_DELAY_SEC = 1.0     # time between automatic polls
REQUEST          = "data"  # poll command

#I2C_ADDRESS     = 0x43    # I2C device address for TinyFX

def worker_loop(master, stop_event, lock):
    '''
    Runs until stop_event is set.
    Repeatedly sends a request to the slave.
    '''
    print("Worker thread started")

    try:
        while not stop_event.is_set():
            with lock:
                response = master.send_request(REQUEST)
            if response == REQUEST:
                print("response: {}".format(response))
            else:
                print("response: {}".format(response))
            time.sleep(WORKER_DELAY_SEC)
    finally:
        print("worker thread stopping")

def main():

    worker_thread = None
    stop_event    = Event()
    i2c_lock      = Lock()
    i2c_address = I2C_ADDRESS
    prompt = "► "

    try:

        parser = argparse.ArgumentParser(description='I2C master remote control')
        parser.add_argument('--address',
                type=lambda x: int(x, 0), default=I2C_ADDRESS,
                help='I2C device address (default: 0x{:02x})'.format(I2C_ADDRESS))
        args = parser.parse_args()
        i2c_address = args.address
        print('connecting to device at 0x{:02X}…'.format(i2c_address))
        master = I2CMaster(i2c_id=I2C_ID, i2c_address=i2c_address)
        master.enable()
        print('\nEnter command string to send (Ctrl-C or "quit" to exit):')

        last_user_msg = None
        while True:
            user_msg = input(prompt)

            if not user_msg:
                continue
            elif last_user_msg is not None and user_msg == 'r':
                # repeat last command
                user_msg = last_user_msg
            elif user_msg.strip() == 'quit':
                break
            elif user_msg == 'go':
                if worker_thread and worker_thread.is_alive():
                    print("worker already running")
                else:
                    stop_event.clear()
                    worker_thread = Thread(target=worker_loop, args=(master, stop_event, i2c_lock), daemon=True,)
                    worker_thread.start()
                continue
            elif user_msg == 'stop':
                if worker_thread and worker_thread.is_alive():
                    stop_event.set()
                    worker_thread.join()
                else:
                    print("worker not running")
                continue

            print('user msg: {}'.format(user_msg))
            with i2c_lock:
                response = master.send_request(user_msg)
            print('response: {}'.format(response))
            last_user_msg = user_msg

    except OSError as e:
        print('unable to connect with device at 0x{:02X}'.format(i2c_address))
    except KeyboardInterrupt:
        print('Ctrl-C caught, exiting…')
    except Exception as e:
        print('error: {}'.format(e))
    finally:
        # clean shutdown
        if worker_thread and worker_thread.is_alive():
            stop_event.set()
            worker_thread.join()

if __name__ == '__main__':
    main()

#EOF
