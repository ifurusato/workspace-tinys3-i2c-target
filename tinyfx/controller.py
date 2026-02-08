#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2026 by Ichiro Furusato. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License.
#
# author:   Ichiro Furusato
# created:  2025-11-16
# modified: 2026-02-08
#
# A Controller for use with the Pimoroni TinyFX.

import os
import sys
import time
import asyncio
from collections import deque
import math, random
from machine import Timer
from machine import RTC

from tiny_fx import TinyFX
from manual_player import ManualPlayer
from settable import SettableFX
from settable_blink import SettableBlinkFX
#from pir import PassiveInfrared

from colors import*
from message_util import pack_message

class Controller:
    _AUTOSTART_SERVICES = True           # auto-start services after delay
    _AUTOSTART_DELAY_MS = 7000           # delay in milliseconds before auto-start
    # pre-packed constant responses
    _PACKED_ACK  = pack_message('ACK')   # acknowledge okay
    _PACKED_NACK = pack_message('NACK')  # acknowledge bad command
    _PACKED_ERR  = pack_message('ERR')   # processing error occurred
    _PACKED_PING = pack_message('PING')  # processing error occurred
    '''
    A controller for command strings received from the I2CSlave.

    Args:
        pixel:    an instance of the Pixel class, provides NeoPixel support
    '''
    def __init__(self, pixel=None):
        self._startup_ms = time.ticks_ms()
        self._slave = None
        # TinyFX specific configuration
        self._tinyfx   = TinyFX(init_wav=True, wav_root='/sounds')
        self._rgbled   = self._tinyfx.rgb
        self._playing  = False
        # channel definitions
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
        # neopixel support, with initial blink
        self._pixel = pixel # optional argument
        self._show_color(COLOR_CYAN)
        time.sleep_ms(100)
        self._show_color(COLOR_BLACK)
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

    # TinyFX ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def ch1(self, enable):
        self._channel1_fx.set(enable)

    def _get_channel(self, channel, blinking=False):
        '''
        The channel argument is included in case you want to customise what
        is returned per channel, e.g., channel 1 below.
        '''
        if blinking:
            if channel == 1:
                # we use a more 'irrational' speed so that the two blinking channels almost never synchronise
                return SettableBlinkFX(speed=0.66723, phase=0.0, duty=0.25)
            else:
                return SettableBlinkFX(speed=0.5, phase=0.0, duty=0.015)
        else:   
            return SettableFX(brightness=0.8)

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

    def _print_help(self):
        print('''
available commands:
  help                                 # prints this help
  time get | set <timestamp>           # set/get RTC time
  pixel off | <color> | <n> <color>    # control NeoPixel
  persist on | off                     # persist pixel after setting
  rgb <n> <red> <green> <blue>         # set NeoPixel to RGB
  heartbeat on | off                   # control heartbeat flash
  ping                                 # returns "PING"
  data                                 # return sample data
  reset                                # force hardware reset

  all on | off                         # turn all LED channels on or off
  play <name>                          # play a sound
  sounds                               # display available sounds
  colors                               # display available colors
''')

    def process(self, cmd):
        '''
        Processes the callback from the I2C slave, returning 'ACK', 'NACK' or 'ERR'.
        See _print_help()
        '''
#       print("cmd: '{}'".format(cmd))
        _show_state = True
        if _show_state:
            self._stop_at = time.ticks_add(time.ticks_ms(), 1000)  # stop 1 second later
        _exit_color = COLOR_BLACK # default
        self._show_color(COLOR_CYAN)
        try:
            parts = cmd.lower().split()
            if len(parts) == 0:
                _exit_color = COLOR_RED
                return self._PACKED_ERR
            _arg0 = parts[0]
            _arg1 = parts[1] if len(parts) > 1 else None
            _arg2 = parts[2] if len(parts) > 2 else None
            _arg3 = parts[3] if len(parts) > 3 else None
            _arg4 = parts[4] if len(parts) > 4 else None
#           print("cmd: '{}'; arg0: '{}'; arg1: '{}'; arg2: '{}'; arg3: '{}'; arg4: '{}'".format(cmd, _arg0, _arg1, _arg2, _arg3, _arg4))

            if _arg0 in ['all', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6'] and len(parts) == 2:
                print('A. arg0: {}; arg1: {}'.format(_arg0, _arg1))
                if _arg0 == 'all':
                    if _arg1 == 'on':
                        for fx in self._player.effects:
                            fx.set(True)
#                       self._enable_heartbeat(True)
                        _exit_color = COLOR_DARK_GREEN
                        return self._PACKED_ACK
                    elif _arg1 == 'off':
                        for fx in self._player.effects:
                            fx.set(False)
#                       self._enable_heartbeat(False)
#                       self._show_color('black')
                        _exit_color = COLOR_DARK_GREEN
                        return self._PACKED_ACK
                    else:
                        print("unrecognised action: '{}'".format(_arg1))
                        _exit_color = COLOR_RED
                        return self._PACKED_ERR
                else:   
                    print('B. arg0: {}; arg1: {}'.format(_arg0, _arg1))
                    fx = self._channel_map[_arg0]
                    print('C. fx: {}'.format(fx))
                    if fx is None:
                        print("no channel for argument: '{}'".format(_arg0))
                        _exit_color = COLOR_RED
                        return self._PACKED_ERR
                    elif _arg1 == 'on':
                        print('fx on: {}'.format(fx))
                        fx.set(True)
                        _exit_color = COLOR_DARK_GREEN
                        return self._PACKED_ACK
                    elif _arg1 == 'off':
                        print('fx off: {}'.format(fx))
                        fx.set(False)
                        _exit_color = COLOR_DARK_GREEN
                        return self._PACKED_ACK
                    else:
                        print("unrecognised action: '{}'".format(_arg1))
                        _exit_color = COLOR_RED
                        return self._PACKED_ERR

            elif _arg0 == "play":
                self._enqueue(self._play, cmd)
                _exit_color = COLOR_DARK_GREEN
                return self._PACKED_ACK

            elif _arg0 == "help":
                self._enqueue(self._print_help)
                _exit_color = COLOR_DARK_GREEN
                return self._PACKED_ACK

            elif _arg0 == "sounds":
                self._enqueue(self._sound_cat)
                _exit_color = COLOR_DARK_GREEN
                return self._PACKED_ACK

            elif _arg0 == "colors":
                self._enqueue(self._color_cat)
                _exit_color = COLOR_DARK_GREEN
                return self._PACKED_ACK

            elif _arg0 == "time":
#               print('time: {}, {}'.format(_arg1, _arg2))
                if _arg1 == 'set':
                    _exit_color = COLOR_DARK_GREEN
                    return self._set_time(_arg2)
                elif _arg1 == 'get':
                    _exit_color = COLOR_DARK_GREEN
                    return pack_message(self._rtc_to_iso(RTC().datetime()))
                _exit_color = COLOR_RED
                return self._PACKED_ERR

            elif _arg0 == "pixel":
                if _arg1 == 'off' or _arg1 == 'clear':
                    color = COLOR_BLACK
                else:
                    color = self._get_color(_arg1, _arg2)
                if not color:
                    print("ERROR: could not find color: arg1: '{}'; arg2: '{}'".format(_arg1, _arg2))
                    _exit_color = COLOR_RED
                    return self._PACKED_ERR
                else:
                    # any calls to pixel disable heartbeat
                    self._enable_heartbeat(False)
                    _show_state = False
                    self._show_color(color)
                    return self._PACKED_ACK

            elif _arg0 == "persist":
                if _arg1 == 'on':
                    self._pixel_persist = True
                    _exit_color = COLOR_BLACK # otherwise it'd be on
                    return self._PACKED_ACK
                elif _arg1 == 'off':
                    self._pixel_persist = False
                    _exit_color = COLOR_DARK_GREEN
                    return self._PACKED_ACK
                else:
                    print("ERROR: unrecognised persist argument: {}'".format(_arg1))
                    _exit_color = COLOR_RED
                    return self._PACKED_ERR

            elif _arg0 == "heartbeat":
                if _arg1 == 'on':
                    self._pixel_persist = False # contradictory, so off
                    self._enable_heartbeat(True)
                    _exit_color = COLOR_DARK_GREEN
                    return self._PACKED_ACK
                elif _arg1 == 'off':
                    self._enable_heartbeat(False)
                    _exit_color = COLOR_DARK_GREEN
                    return self._PACKED_ACK
                else:
                    print("ERROR: unrecognised argument: '{}'".format(_arg1))
                    _exit_color = COLOR_RED
                    return self._PACKED_ERR

            elif _arg0 == "rgb":
                # e.g., rgb 3 130 40 242
                index = int(_arg1)
                red   = int(_arg2)
                green = int(_arg3)
                blue  = int(_arg4)
                # any calls to rgb disable heartbeat
                self._enable_heartbeat(False)
                _show_state = False
                self._show_color(color)
                return self._PACKED_ACK

            elif _arg0 == "ping":
                _exit_color = COLOR_DARK_GREEN
                return self._PACKED_PING

            elif _arg0 == "data": # data request (TBD)
                _message = self._get_data()
                _exit_color = COLOR_FUCHSIA
                return pack_message(_message)

            elif _arg0 == "reset":
                import machine

                print('performing microcontroller reset…')
                machine.reset()
                return self._PACKED_ACK

            else:
                print("WARNING: unrecognised command: '{}'{}{}{}".format(
                        cmd,
                        "; arg0: '{}'".format(_arg0) if _arg0 else '',
                        "; arg1: '{}'".format(_arg1) if _arg1 else '',
                        "; arg2: '{}'".format(_arg2) if _arg2 else ''))
                _exit_color = COLOR_ORANGE
                return self._PACKED_NACK
            _exit_color = COLOR_DARK_GREEN
            return self._PACKED_ACK

        except Exception as e:
            print("ERROR: {} raised by controller: {}".format(type(e), e))
            sys.print_exception()
            _exit_color = COLOR_RED
            return self._PACKED_ERR
        finally:
            if _show_state:
                self._show_color(_exit_color)

    # ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

    def _get_data(self):
        '''
        Return data (TBD).
        '''
        _data = '0000 1111 2222 3333 4444 5555 6666 7777'
#       print('data: {} chars.'.format(len(_data)))
        return _data

    def _on_command(self, cmd):
        '''
        The callback from the I2C slave, passes the command on for processing,
        returning the result.
        '''
        return self.process(cmd)

    def _led_off(self, timer=None):
        self._show_color(COLOR_BLACK)

    def _start_services(self):
        time_elapsed = time.ticks_ms() - self._startup_ms
        print('starting services after {}ms'.format(time_elapsed))
        self._enable_heartbeat(True)
        pass # whatever services to be started after a delay

    def _enable_heartbeat(self, enabled):
        self._heartbeat_enabled = enabled
        if not enabled:
            self._timer0.deinit()

    def _beat(self):
        self._show_color(COLOR_MEDIUM_CYAN)
        self._timer0.deinit()
        self._timer0.init(period=20, mode=Timer.PERIODIC, callback=self._led_off)

    def _heartbeat(self, delta_ms):
        self._heartbeat_timer += delta_ms
        if self._heartbeat_state:
            if self._heartbeat_timer >= self._heartbeat_on_time_ms:
                self._heartbeat_state = False
                self._heartbeat_timer = 0
        else:
            if self._heartbeat_timer >= self._heartbeat_off_time_ms:
                self._heartbeat_state = True
                self._beat()
                self._heartbeat_timer = 0

    def _get_color(self, name, second_token):
        if second_token: # e.g., "dark cyan"
            name = '{} {}'.format(name, second_token)
        return Color.get(name)

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

    def _set_rotation_pending(self, t):
        self._rotation_pending = True

    def _parse_timestamp(self, ts):
        year    = int(ts[0:4])
        month   = int(ts[4:6])
        day     = int(ts[6:8])
        hour    = int(ts[9:11])
        minute  = int(ts[11:13])
        second  = int(ts[13:15])
        weekday = 0
        subsecs = 0
        return (year, month, day, weekday, hour, minute, second, subsecs)

    def _rtc_to_iso(self, dt):
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(dt[0], dt[1], dt[2], dt[4], dt[5], dt[6])

    def _get_time(self):
        return time.time()

    def _set_time(self, timestamp):
        try:
            print('time before: {}'.format(self._rtc_to_iso(RTC().datetime())))
            RTC().datetime(self._parse_timestamp(timestamp))
            print('time after:  {}'.format(self._rtc_to_iso(RTC().datetime())))
            return self._PACKED_ACK
        except Exception as e:
            print("ERROR: {} raised by tinyfx controller: {}".format(type(e), e))
            return self._PACKED_ERR

#EOF
