#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License.
#
# author:   Ichiro Furusato
# created:  2026-02-09
# modified: 2026-02-12

import os
import asyncio
import time
from machine import Timer
from collections import deque
from controller import Controller
from colors import *
from pixel import Pixel

from tiny_fx import TinyFX
from manual_player import ManualPlayer
from settable import SettableFX
from settable_blink import SettableBlinkFX
#from pir import PassiveInfrared

class TinyFxPixel:
    def __init__(self, rgbled=None):
        self._rgbled = rgbled

    @property
    def pixel_count(self):
        return 1

    def set_color(self, index=None, color=None):
        if color is None or color == COLOR_BLACK:
            color = COLOR_BLACK
        elif isinstance(color, str):
            color = Color.get(color)
        if color:
            self._rgbled.set_rgb(*color)
        else:
            print("ERROR: unknown color name: {}".format(color))

class TinyFxController(Controller):
    '''
    An implementation using a WeAct STM32F405 optionally connected to a NeoPixel
    strip and a 24 pixel NeoPixel ring.
    '''
    def __init__(self, config):
        self._tinyfx   = TinyFX(init_wav=True, wav_root='/sounds')
        super().__init__(config)
#       self._pixel_off_pending = False
        self._playing  = False
        # channel definitions
        self._brightness  = 0.3
        self._blink_duty  = 0.25
        self._blink_speed = 0.66723
        blink_channels = [True, False, False, False, False, False] # channel 1 blinks
        self._channel1_fx = self._get_channel(1, blink_channels[0])
        self._channel2_fx = self._get_channel(2, blink_channels[1])
        self._channel3_fx = self._get_channel(3, blink_channels[2])
        self._channel4_fx = self._get_channel(4, blink_channels[3])
        self._channel5_fx = self._get_channel(5, blink_channels[4])
        self._channel6_fx = self._get_channel(6, blink_channels[5])
        # set up the effects to play
        self._player = ManualPlayer(self._tinyfx.outputs)
        self._player.effects = [
            self._channel1_fx,
            self._channel2_fx,
            self._channel3_fx,
            self._channel4_fx,
            self._channel5_fx,
            self._channel6_fx
        ]
        # name map of channels (you can add aliases here)
        self._channel_map = {
            'ch1': self._channel1_fx,
            'ch2': self._channel2_fx,
            'ch3': self._channel3_fx,
            'ch4': self._channel4_fx,
            'ch5': self._channel5_fx,
            'ch6': self._channel6_fx
        }
        # heartbeat feature
        self._heartbeat_enabled     = False
        self._heartbeat_on_time_ms  = 50
        self._heartbeat_off_time_ms = 2950
        self._heartbeat_timer = 0
        self._heartbeat_state = False
        self._stop_at = None
        self._pixel_persist = False
        # instantiate ring
        self._timer0 = Timer() # no ID on RP2
        self._services_started   = False
        # PIR sensor (no Timer: you can poll it manually if used)
#       self._pir_sensor    = PassiveInfrared()
        self._pir_triggered = False
        self._pir_enabled   = False # default disabled
        # start asyncio private dispatcher
        self._loop        = asyncio.get_event_loop()
        self._queue       = deque((), 8)
        self._busy        = False
        self._loop.create_task(self._dispatcher())
        self._play('arming-tone')
        print('ready.')

    def _create_pixel(self):
        self._rgbled = self._tinyfx.rgb
        self._pixel  = TinyFxPixel(self._rgbled)
        # neopixel support, with initial blink
        self._show_color(COLOR_CYAN)
        time.sleep_ms(100)
        self._show_color(COLOR_BLACK)
        return self._pixel

    def _enqueue(self, fn, *args, **kwargs):
        self._queue.append((fn, args, kwargs))
        return True

    async def _dispatcher(self):
        while True:
            if self._queue and not self._busy:
                fn, args, kwargs = self._queue.popleft()
                self._busy = True
                try:
                    fn(*args, **kwargs)
                except Exception as e:
                    print("{} raised processing job: {}".format(type(e), e))
                finally:
                    self._busy = False
            await asyncio.sleep_ms(0)

    def _create_pixel_timer(self):
        from machine import Timer

        self._pixel_timer = Timer()
        self._pixel_timer.init(freq=self._pixel_timer_freq_hz, callback=self._led_off)

    # TinyFX ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _get_channel(self, channel, blinking=False):
        '''
        The channel argument is included in case you want to customise what
        is returned per channel, e.g., channel 1 below.
        '''
        if blinking:
            if channel != 1:
                # we use a more 'irrational' speed so that the two blinking channels almost never synchronise
                return SettableBlinkFX(speed=self._blink_speed, phase=0.0, duty=self._blink_duty)
            else:
                return SettableBlinkFX(speed=0.5, phase=0.0, duty=0.015)
        else:
            return SettableFX(brightness=self._brightness)

    def _get_pir(self):
        '''
        A placeholder for PIR processing, just returns "not implemented".
        '''
        return "NOT_IMPL"

    # public API ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    @property
    def pixel(self):
        return self._pixel

    def tick(self, delta_ms):
        # TinyFX PWM
        self._player.update(delta_ms)
        if self._heartbeat_enabled:
            self._heartbeat(delta_ms)
        if self._stop_at is not None:
            if time.ticks_diff(time.ticks_ms(), self._stop_at) >= 0:
                self._stop_at = None
                if not self._pixel_persist:
                    self._show_color(COLOR_BLACK)
        if self._AUTOSTART_SERVICES and not self._services_started:
            if time.ticks_diff(time.ticks_ms(), self._startup_ms) >= self._AUTOSTART_DELAY_MS:
                self._services_started = True
                self._start_services()

    def set_slave(self, slave):
        self._slave = slave
        self._slave.add_callback(self._on_command)

    def print_help(self):
        super().print_help()
        print('''    all on | off                            # turn all LED channels on or off
    ch[1-6] on | off                        # turn an LED channel on or off
    play <name>                             # play a sound
    sounds                                  # display available sounds
    colors                                  # display available colors
''')

    def pre_process(self, cmd, arg0, arg1, arg2, arg3, arg4):
        '''
        Pre-process the arguments, returning a response and color if a match occurs.
        Such a match precludes further processing.
        '''
#       print("pre-process command '{}' with arg0: '{}'; arg1: '{}'; arg2: '{}'; arg3: '{}'; arg4: '{}'".format(cmd, arg0, arg1, arg2, arg3, arg4))
        parts = cmd.split()

        if arg0 == "__extend_here__":
            return None, None

        elif arg0 in ['all', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6'] and len(parts) == 2:
            print('A. arg0: {}; arg1: {}'.format(arg0, arg1))
            if arg0 == 'all':
                if arg1 == 'on':
                    for fx in self._player.effects:
                        fx.set(True)
#                   self._enable_heartbeat(True)
                    return Controller._PACKED_ACK, COLOR_DARK_GREEN
                elif arg1 == 'off':
                    for fx in self._player.effects:
                        fx.set(False)
#                   self._enable_heartbeat(False)
#                   self._show_color('black')
                    return Controller._PACKED_ACK, COLOR_DARK_GREEN
                else:
                    print("unrecognised action: '{}'".format(arg1))
                    return Controller._PACKED_ERR, COLOR_RED
            else:   
                print('B. arg0: {}; arg1: {}'.format(arg0, arg1))
                fx = self._channel_map[arg0]
                print('C. fx: {}'.format(fx))
                if fx is None:
                    print("no channel for argument: '{}'".format(arg0))
                    return Controller._PACKED_ERR, COLOR_RED
                elif arg1 == 'on':
                    print('fx on: {}'.format(fx))
                    fx.set(True)
                    return Controller._PACKED_ACK, COLOR_DARK_GREEN
                elif arg1 == 'off':
                    print('fx off: {}'.format(fx))
                    fx.set(False)
                    return Controller._PACKED_ACK, COLOR_DARK_GREEN
                else:
                    print("unrecognised action: '{}'".format(arg1))
                    return Controller._PACKED_ERR, COLOR_RED

        elif arg0 == "play":
            self._enqueue(self._play, cmd)
            return Controller._PACKED_ACK, COLOR_DARK_GREEN

        elif arg0 == "sounds":
            self._enqueue(self._sound_cat)
            return Controller._PACKED_ACK, COLOR_DARK_GREEN
        
        elif arg0 == "colors":
            self._enqueue(self._color_cat)
            return Controller._PACKED_ACK, COLOR_DARK_GREEN

        else:
            return None, None


    def _sound_cat(self):
        print('\navailable sounds:')
        files = os.listdir('sounds')
        names = [f.split('.')[0] for f in files]
        columns = 4
        width = 24
        for i in range(0, len(names), columns):
            row = names[i:i+columns]
            print("  " + ("".join("{:<{w}}".format(name, w=width) for name in row)))
        print('')

    def _color_cat(self):
        print('\navailable colors:')
        names = [c.name for c in Color.all_colors()]
        columns = 4
        width = 24
        for i in range(0, len(names), columns):
            row = names[i:i+columns]
            print("  " + ("".join("{:<{w}}".format(name, w=width) for name in row)))
        print('')

    def _play(self, cmd):
        parts = cmd.split()
        if len(parts) < 2:
            sound_name = cmd
        else:
            sound_name = parts[1]
        try:
            # check exists
            file_name = '{}.wav'.format(sound_name)
            path_name = 'sounds/{}'.format(file_name)
            os.stat(path_name)
            self._playing = True
            self._tinyfx.wav.play_wav(file_name)
            print('playing: {}…'.format(sound_name))
        except Exception as e:
            print("sound name '{}' not found.".format(sound_name))
        finally:
            self._playing = False

    def _show_color(self, color):
        if isinstance(color, str):
            color = Color.get(color)     
        if color:
            if self._pixel:
                self._pixel.set_color(0, color)
            else:
                self._rgbled.set_rgb(*color)
        else:
            print("ERROR: unknown color name: {}".format(color))

#EOF
