#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License.
#
# author:   Ichiro Furusato
# created:  2026-02-09
# modified: 2026-02-09

import sys
from controller import Controller
from colors import *
from pixel import Pixel

class PixelState:
    def __init__(self, color=COLOR_BLACK, phase=0.0):
        self.base_color = color
        self.color = color.rgb
        self.phase = phase

    def is_active(self):
        return self.base_color != COLOR_BLACK

    def reset(self):
        self.base_color = COLOR_BLACK
        self.color = self.base_color.rgb
        self.phase = 0.0

class STM32Controller(Controller):
    STRIP_PIN = 'B12'
    RING_PIN  = 'B14'
    '''
    An implementation using a WeAct STM32F405 optionally connected to a NeoPixel
    strip and a 24 pixel NeoPixel ring.
    '''
    def __init__(self):
        self._pixel = Pixel(pin=STM32Controller.RING_PIN, pixel_count=1, brightness=0.1)
        super().__init__(self._pixel)
        # ready

    def _create_pixel_timer(self):
        from pyb import Timer
        
        self._pixel_timer = Timer(4)
        self._pixel_timer.init(freq=self._pixel_timer_freq_hz, callback=self._led_off)

#EOF
