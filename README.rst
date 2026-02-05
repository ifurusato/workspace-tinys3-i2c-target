*****************
TinyS3 I2C Target
*****************

An I2CTarget implementation for I2C-based remote control of a UM TinyS3, an ESP32-S3.

This is a highly simplified version of the implementation used on KRZ0S, the operating
system for the KRZ04 robot, see the `krzos`_ repository.

.. _krzos: https://github.com/ifurusato/krzos

This permits bidirectional transactions between master and slave, with data returned
up to 32 characters. Round-trip performance is about 11ms, but if you are not requesting
returned data (other than "ACK" or "ERR") this can be set down to ~3-5ms. This setting
may be found in ``tinys3_controller/i2c_master.py``.

The current Controller implementation is largely focused on controlling the TinyS3's
NeoPixel, but is intended to be expanded as per more expansive project requirements.


Requirements
************

Requires Python 3.8.5 or newer, written using Python 3.11.2.
Support for I2CTarget requires MicroPython v1.27.0 installed on the TinyS3.

This was developed using an Unexpected Maker TinyS3 and a Raspberry Pi, but
could easily be adapted to different hardware.


Installation
************

Copy the ``./upy/`` files to your TinyS3. When restarted it will blink once initially,
and then after 7 seconds "services" will start and a heartbeat blink will occur
every second.

Executing ``remote.py`` will start the CLI application. Documentation for acceptable
commands may be found in the Controller class' ``process()`` method.


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

* 2026-02-05: initial posting


Support & Liability
*******************

This project comes with no promise of support or acceptance of liability. Use at
your own risk.


Copyright & License
*******************

The NeoPixel driver for MicroPython is distributed under the MIT license;
Copyright (c) 2016 Damien P. George, 2021 Jim Mussared.

The TinyS3 Helper Library is distribued under an MIT license, Copyright 2022
Seon Rozenblum, Unexpected Maker.

All other contents (including software, documentation and images) Copyright 2026
by Ichiro Furusato. All rights reserved. Software and documentation are distributed
under the MIT License, see LICENSE file included with the project.

