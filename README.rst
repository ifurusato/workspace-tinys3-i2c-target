*****************
TinyS3 I2C Target
*****************

An I2CTarget implementation for I2C-based remote control of a UM TinyS3, an ESP32-S3.

This is a highly simplified version of the implementation used on KRZ0S, the operating
system for the KRZ04 robot, see the `krzos`_ repository.

.. _krzos: https://github.com/ifurusato/krzos

This permits bidirectional transactions between master and slave, with data
returned up to 62 characters, using a CRC8 checksum. Round-trip performance
corresponds to message length, designed for a 39 characters packet requiring
an 11ms delay, but if you are requesting shorter packets or only acknowledgements
(e.g., "ACK" or "ERR") this can be set lower, down to ~3-5ms. This setting may
be found in ``tinys3_controller/i2c_master.py``.

The current master and slave implementation is intended as a demonstration
controlling the TinyS3's NeoPixel, and is intended to be modified as necessary.

This was developed using CPython on a Raspberry Pi as I2C master, and MicroPython
on an Unexpected Maker TinyS3 as slave, but could easily be adapted to different
hardware. Typically, the SDA, SCL and NeoPixel pins will need to be changed.


Requirements
************

Requires Python 3.8.5 or newer, written using Python 3.11.2.

Support for `I2CTarget`_ requires `MicroPython`_ v1.27.0 or newer installed on
the microcontroller.

.. _I2CTarget: https://docs.micropython.org/en/latest/library/machine.I2CTarget.html
.. _MicroPython: https://micropython.org/download/UM_TINYS3/


Installation
************

Copy the ``./upy/`` files to your TinyS3. I recommend `rshell`_ or `mpremote`_, though
any tool will do.

.. _rshell: https://github.com/dhylands/rshell
.. _mpremote: https://docs.micropython.org/en/latest/reference/mpremote.html



Usage
*****

The I2C slave should start from a hardware reset, but you can start it from the
Python REPL via "import main".

The current master and slave code is meant as a demonstration, and can be modified
as necessary. It currently just controls the NeoPixel on the TinyS3.

Executing ``remote.py`` will start the CLI application. The TinyS3 must already be
running its ``main.py`` script. Typing Ctrl-C will end the session.

On the master, the "go" command will repeat a preconfigured command every second,
which could be used for testing or a repeating query. "stop" will halt the loop.

When the TinyS3 is restarted it will blink once initially, and then after 7 seconds
its "services" will start and a heartbeat blink will occur every second. The services
and the startup delay are meant to be expanded into an actual application usage. This
feature can be disabled if not needed.

The commands are:

    time get | set <timestamp>           # set/get RTC time
    pixel off | <color> | <n> <color>    # control NeoPixel
    persist on | off                     # persist pixel after setting
    rgb <n> <red> <green> <blue>         # set NeoPixel to RGB (0-255, 0-255, 0-255)
    heartbeat on | off                   # control heartbeat flash
    ping                                 # returns "PING"
    data                                 # return sample data
    reset                                # force hardware reset

Color names are enumerated in colors.py. You can use "pink" or "dark cyan"
without quotes, e.g.,

    pixel dark cyan

The NeoPixel will automatically turn off after 1 second. To keep it on, use
"persist on".

The heartbeat, which blinks the NeoPixel, can be turned on or off. Setting
the NeoPixel will disable it automatically.

If the slave performance is too slow (for any reason), the slave will generally
return the command sent to it (which is what's in its memory buffer prior to
being processed), otherwise "ACK", "ERR" or specific data.


Files
*****

Program files include::

    remote.py             # the CLI remote controller

    tinys3_controller:    # the library directory
        __init__.py
        i2c_master.py     # the abstract I2C master class
        message_util.py   # handles message packing and unpacking, CRC8 checksums

    upy:
        boot.py
        colors.py         # a pseudo-enum of predefined color names
        controller.py     # the controller for handling incoming commands
        ctrl.py           # the slave-side CLI
        i2c_slave.py      # the I2C slave implementation
        main.py           # entry point into the application
        message_util.py   # same file as above
        neopixel.py       # standard NeoPixel implementation
        pixel.py          # wraps NeoPixel functionality
        tinys3.py         # TinyS3 utility class (from UM)

.. Yes, message_util.py is duplicated. I could be clever but prefer they are independent even if identical.


Status
******

* 2026-02-07: modified I2CSlave constructor to require all parameters, no fixed defaults; fixed NeoPixel persistence.
* 2026-02-05: initial posting


Support & Liability
*******************

This project comes with no promise of support or acceptance of liability.
Use at your own risk.


Copyright & License
*******************

The NeoPixel driver for MicroPython is distributed under the MIT license;
Copyright © 2016 Damien P. George, 2021 Jim Mussared.

The TinyS3 Helper Library is distributed under the MIT license,
Copyright © 2022 Seon Rozenblum, Unexpected Maker.

All other contents (including software, documentation and images)
Copyright © 2026 Ichiro Furusato. All rights reserved. Software and
documentation are distributed under the MIT License, see LICENSE file
included with the project.

