#! /usr/bin/env python
from __future__ import print_function
import logging
logging.getLogger(__name__).setLevel(logging.INFO)

import os,sys,time
#import yaml

import signal
from snowboy import snowboydecoder

interrupted = False

def signal_handler(signal, frame):
    global interrupted
    interrupted = True

def interrupt_callback():
    global interrupted
    return interrupted

# capture SIGINT signal, e.g., Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

from play_audio import play_music
from microphone import microphone
from alexa_query import internet_on,alexa_query
from busman import busman_query

path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))

alexa_tmp = '/tmp/alexa-pi'

if sys.platform.startswith('linux'):
  alexa_tmp = '/dev/shm/alexa-pi'

try: os.makedirs(os.path.join(alexa_tmp,'bak'))
except: pass

raw_recording = os.path.join(alexa_tmp,'recording.raw')
mp3_response = os.path.join(alexa_tmp,'response.mp3')
http_log = os.path.join(alexa_tmp,'http.log')


if sys.platform.startswith('linux'):
    # handle alsa-lib error log things
    from ctypes import CFUNCTYPE,cdll,c_char_p, c_int
    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    def py_error_handler(filename, line, function, err, fmt): pass #print 'messages are yummy'
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)

def ding(): snowboydecoder.play_audio_file(snowboydecoder.DETECT_DING)

# def handle():
#     with open(raw_recording,'rb') as raw:
#         directives = alexa_query(raw, mp3_response, http_log)
#         if 'speak' in directives:
#             play_music(mp3_response,60000)
#         return directives

# def start2():
#     while True:
#         ding()
#         if record_to_file(raw_recording):
#             directives = handle()

def handle_alexa():
    wait = True #False
    while True:
        ding()
        mic = microphone(wait)
        #logging.warn(('start microphone',wait))
        #logging.warn(('end microphone',wait))
        directives = alexa_query(mic, mp3_response, http_log)
        logging.warn(('directives:', directives.keys()))
        if 'speak' in directives:
            play_music(mp3_response,60000)
        #if len(directives) > 0 and not 'listen' in directives:
        if not 'listen' in directives:
            break
        wait = True
    logging.warn(('[Snowboy Listening...]'))
    ding()


def handle_okbus():
    wait = False
    while True:
        ding()
        mic = microphone(wait)
        directives = busman_query(mic)
        logging.warn(('directives:', directives.keys()))
        if len(directives) > 0 and not 'listen' in directives:
            break
        wait = True
    logging.warn(('[Snowboy Listening...]'))
    ding()

if __name__ == "__main__":

    while not internet_on():
        sys.stderr.write('.')

    #start2()

    models = [
        'pmdl/Alexa.pmdl',
        # 'pmdl/ok bus.pmdl'
    ]

    sensitivity = [
        0.45,
        # 0.45
    ]

    callbacks = [
        handle_alexa,
        # handle_okbus
    ]

    # test
    while True:
        handle_alexa()
        logging.warn(('handle_alexa finished'))

    detector = snowboydecoder.HotwordDetector(models, sensitivity=sensitivity)
    logging.warn(('[Snowboy Listening...]'))
    ding()

    # main loop
    detector.start(detected_callback=callbacks,
                   interrupt_check=interrupt_callback,
                   sleep_time=0.03)

    detector.terminate()


# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
