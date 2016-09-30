#! /usr/bin/env python
import os,sys,time,logging
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

#import play_audio
#import record_audio
#import alexa_query

from play_audio import play_music
from record_audio import record_to_file
from alexa_query import internet_on,alexa_query

path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))

sound_chime1 = os.path.join(path,'sounds/chime1.mp3') # listening
sound_chime2 = os.path.join(path,'sounds/chime2.mp3') # querying
sound_chime3 = os.path.join(path,'sounds/chime3.mp3') # something wrong

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


#def mute(): os.system('amixer -q set Master mute')
#def unmute(): os.system('amixer -q set Master unmute 45%; amixer -q set Front unmute; amixer -q set Headphone unmute')

def ding(): snowboydecoder.play_audio_file(snowboydecoder.DETECT_DING)

def handle():
    directives = alexa_query(raw_recording, mp3_response, http_log)
    if 'speak' in directives:
        play_music(mp3_response,60000)
    return directives

def start2():
    while True:
        ding()
        if record_to_file(raw_recording):
            directives = handle()

def handle_snowboy():
    wait = False
    while True:
        ding()
        if record_to_file(raw_recording, wait=wait):
            directives = handle()
            if len(directives) > 0 and not 'listen' in directives:
                break
            wait = True
    print('directives:', directives.keys())
    print('Snowboy Listening... Press Ctrl+C to exit')
    ding()

if __name__ == "__main__":

    while not internet_on():
        sys.stderr.write('.')

    #start2()

    model = 'pmdl/Alexa.pmdl'
    sensitivity = 0.35
    detector = snowboydecoder.HotwordDetector(model, sensitivity=sensitivity)
    print('Snowboy Listening... Press Ctrl+C to exit')
    ding()

    # main loop
    detector.start(detected_callback=handle_snowboy, #snowboydecoder.play_audio_file,
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
