#! /usr/bin/env python
import os,sys,time,logging

import play_audio
import record_audio
import alexa_query

from play_audio import play_music
from record_audio import record_to_file
from alexa_query import internet_on,alexa_query

path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))

sound_chime1 = os.path.join(path,'sounds/chime1.mp3') # listening
sound_chime2 = os.path.join(path,'sounds/chime2.mp3') # querying
sound_chime3 = os.path.join(path,'sounds/chime3.mp3') # something wrong

ramdir = '/dev/shm/alexa-pi'
try: os.makedirs(os.path.join(ramdir,'bak'))
except: pass

raw_recording = os.path.join(ramdir,'recording.raw')
raw_recording_bak = os.path.join(ramdir,'bak/recording.raw')
mp3_response = os.path.join(ramdir,'response.mp3')
mp3_response_bak = os.path.join(ramdir,'bak/response.mp3')
http_log = os.path.join(ramdir,'http.log')
http_log_bak = os.path.join(ramdir,'bak/http.log')




# handle alsa-lib error log things
from ctypes import CFUNCTYPE,cdll,c_char_p, c_int
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt): pass #print 'messages are yummy'
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
asound = cdll.LoadLibrary('libasound.so')
asound.snd_lib_error_set_handler(c_error_handler)




def mute(): os.system('amixer -q set Master mute')
def unmute(): os.system('amixer -q set Master unmute 45%; amixer -q set Front unmute; amixer -q set Headphone unmute')




def start2():

    while True:

        play_music(sound_chime1,5000)

        time.sleep(1.5)

        record_to_file(raw_recording)

        if os.path.exists(raw_recording):

            logging.info('start alexa()')

            play_music(sound_chime2,5000)

            alexa_query(raw_recording, mp3_response, http_log)

            if os.path.exists(mp3_response):
                play_music(mp3_response,60000)
            else:
                play_music(sound_chime3,5000)

            try: os.rename(raw_recording,raw_recording_bak)
            except: pass
            try: os.rename(mp3_response,mp3_response_bak)
            except: pass
            try: os.rename(http_log,http_log_bak)
            except: pass

            if os.path.exists('etc/backup-log.sh'):
                try: os.system('sh etc/backup-log.sh')
                except: pass

            logging.info('finished alexa()')
        else:
            play_music(sound_chime3,5000)

if __name__ == "__main__":

    while internet_on() == False:
        sys.stderr.write('.')

    start2()

# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
