#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Ichiro Furusato
# created:  2025-02-08
# modified: 2025-02-08

from machine import Pin
from colors import *

class PicoPixel:
    def __init__(self, pin=None, pixel_count=1, color_order='GRB', brightness=0.33):
        self._led = Pin(25, Pin.OUT)
        # ready

    def on(self):
        self._led.value(1)

    def off(self):
        self._led.value(0)

    @property
    def pixel_count(self):
        return self._pixel_count

    @property
    def brightness(self):
        return self._brightness

    def rainbow_cycle(self, delay=0.05, steps=-1):
        raise Exception('not implemented.')

    def set_color(self, index=None, color=None):
        if color is None or color == COLOR_BLACK:
            self.off()
        else:
            self.on()

#EOF
