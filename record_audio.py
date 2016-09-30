#
import sys,time
import math

import pyaudio
import audioop

from sys import byteorder
from array import array
from struct import pack

import numpy as np

#from vad import VAD




CHANNELS = 1
FORMAT = pyaudio.paInt16
RATE = 24000
RATE_OUTPUT = 16000

CHUNK_SAMPLES = 240     # 0.01s approx

ABOVE_CHUNKS = 20      # 0.2s
BELOW_CHUNKS = 150     # 1.5s

MIN_CHUNKS = 150       # 1.5s
MAX_CHUNKS = 950       # 9.5s


NORMALIZE_LEVEL = 16384  # 50% of max amp
THRESHOLD_INITIAL_BASE = 0
THRESHOLD_MARGIN = 819  # 1638 ~ 32768 * 0.05, 819 ~ 32768 * 0.025



class color:
    black   = '\033[1;37;40m'
    red     = '\033[1;37;41m'
    green   = '\033[1;37;42m'
    yellow  = '\033[1;37;43m'
    blue    = '\033[1;37;44m'
    magenta = '\033[1;37;45m'
    cyan    = '\033[1;37;46m'
    white   = '\033[1;37;47m'
    nocolor = '\033[0m'


#range0  = color.white
#range1  = color.green
#range2  = color.red
#range3  = color.yellow

range0  = '\033[1;37;42m'
range1  = '\033[1;30;42m'
range2  = '\033[1;31;43m'
range3  = '\033[1;37;43m'
nocolor = '\033[0m'




def print_vumeter(rec_on, fmin,fmax,fthr,msg=''):

    if rec_on:
        rec_state = color.black + ' ' + color.nocolor
    else:
        rec_state = color.red + ' ' + color.nocolor

    pscl = 2.5
    lmin = int(math.floor(pscl*math.log(fmin+1)))
    lmax = int(math.ceil(pscl*math.log(fmax+1)))
    lthr = int(math.ceil(pscl*math.log(fthr+1)))
    lwid = int(math.ceil(pscl*math.log(16383+1)))
    s = ''
    if lmax < lthr:
        if lmin > 0       : s = s + range0 + ' ' * lmin
        if lmax - lmin > 0: s = s + range1 + '>' * ( lmax - lmin )
        if lthr - lmax > 0: s = s + range0 + ' ' * ( lthr - lmax )
        if lwid - lthr > 0: s = s + range3 + ' ' * ( lwid - lthr )
    elif lthr < lmin:
        if lthr > 0       : s = s + range0 + ' ' * lthr
        if lmin - lthr > 0: s = s + range3 + ' ' * ( lmin - lthr )
        if lmax - lmin > 0: s = s + range2 + '>' * ( lmax - lmin )
        if lwid - lmax > 0: s = s + range3 + ' ' * ( lwid - lmax )
    else:
        if lmin > 0       : s = s + range0 + ' ' * lmin
        if lthr - lmin > 0: s = s + range1 + '>' * ( lthr - lmin )
        if lmax - lthr > 0: s = s + range2 + '>' * ( lmax - lthr )
        if lwid - lmax > 0: s = s + range3 + ' ' * ( lwid - lmax )
    s = s + nocolor
    sys.stderr.write('%s [ %s ] %6d %6d %s' % ( rec_state, s, fmin, fthr, msg, ) + '\r')




__rms = THRESHOLD_INITIAL_BASE
__rms_max = __rms_min = __rms
__threshold = __rms + THRESHOLD_MARGIN
__display_time = time.time()
__display_dirty = False

# run for each chunk, ( 1/100s )
def adjust_threshold(rec_blocks):
    "update threshold"

    global __display_time,__threshold,__rms_max,__rms_min,__display_dirty

    # adjust current threshold. to follow-up th_target, within 3000 chunks, ( 30s )
    th_target = __rms + THRESHOLD_MARGIN
    th_delta = th_target - __threshold

    __threshold += th_delta / 100.0 / 30.0
    __rms_max = max(__rms_max,__rms)
    __rms_min = min(__rms_min,__rms)

    # show status at interval 1s
    t_now = time.time()

    if t_now >= __display_time + 0.5:
        if 0 == rec_blocks:
            print_vumeter(False, __rms_min,__rms_max,__threshold)
        else:
            print_vumeter(True, __rms_min,__rms_max,__threshold, ('recording: %5.1f %5.1f' % ( min(0,rec_blocks/1000.0-1.0), rec_blocks/100.0,)))
        __display_time = t_now
        __rms_max = __rms_min = __rms
        __display_dirty = True



#_detector = VAD(fs=24000)


def is_silent(snd_blocks,snd_chunk):
    "Returns 'True' if below the 'silent' threshold"

    global __rms

    __rms = current = audioop.rms(snd_chunk,2)
    #v = _detector.activations(np.array(snd_chunk))
    #sys.stderr.write('%.1f: vad activations: %.1f'%(time.time(),v,)+'\n')

    res = current < __threshold

    adjust_threshold(snd_blocks)

    return res


def normalize(snd_chunk):
    "Average the volume out"
    times = float(NORMALIZE_LEVEL)/max(abs(i) for i in snd_chunk)
    r = array('h')
    for i in snd_chunk:
        r.append(int(i*times))
    return r

def trim(snd_chunk):
    "Trim the blank spots at the start and end"

    def _trim(snd_chunk):
        snd_started = False
        r = array('h')

        for i in snd_chunk:
            if not snd_started and abs(i)>__threshold:
                snd_started = True
                r.append(i)

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_chunk = _trim(snd_chunk)

    # Trim to the right
    snd_chunk.reverse()
    snd_chunk = _trim(snd_chunk)
    snd_chunk.reverse()
    return snd_chunk

def add_silence(snd_chunk, seconds):
    "Add silence to the start and end of 'snd_chunk' of length 'seconds' (float)"
    r = array('h', [0 for i in xrange(int(seconds*RATE))])
    r.extend(snd_chunk)
    r.extend([0 for i in xrange(int(seconds*RATE))])
    return r

def record(wait):
    """
    Record a word or words from the microphone and
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the
    start and end, and pads with 0.5 seconds of
    blank sound to make sure VLC et al can play
    it without getting chopped off.
    """

    # clear dynamic threshold reference time

    global __display_dirty
    __display_dirty = False

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, output=True,
                    frames_per_buffer=CHUNK_SAMPLES)

    t_now = time.time()
    #sys.stderr.write('%.1f: [[record:listening...]]'%(t_now,)+'\n')

    num_silent = 0
    num_noisy = 0
    snd_blocks = 0

    r = array('h')
    snd_frame = array('h') # frame_data.extend(snd_data) = frame to analyze ( 2 * CHUNK_SAMPLES samples )

    while 1:

        t_now = time.time()

        # little endian, signed short
        snd_chunk = array('h', stream.read(CHUNK_SAMPLES, exception_on_overflow=False))

        if byteorder == 'big':
            snd_chunk.byteswap()

        r.extend(snd_chunk)

        if ( len(snd_frame) == 0 ):
            pass
        else:
            snd_frame.extend(snd_chunk)

            silent = is_silent(snd_blocks,snd_frame)

            if 0 == snd_blocks: # check recording start condition

                if wait and silent:
                    num_noisy = 0
                    r = array('h') # truncate buffer
                else:
                    num_noisy += 1
                    if num_noisy >= ABOVE_CHUNKS:
                        if __display_dirty: sys.stderr.write('\n')
                        __display_dirty = False
                        #sys.stderr.write('%.1f: [[record:started]]'%(t_now,)+'\n')
                        snd_blocks = 1

            else: # check recording stop condition

                snd_blocks += 1

                if snd_blocks > MAX_CHUNKS + BELOW_CHUNKS: # ignore if the sample longer than 9.5s
                    if __display_dirty: sys.stderr.write('\n')
                    __display_dirty = False
                    #sys.stderr.write('%.1f: [[record:cancelled]]'%(t_now,)+'\n')
                    dur = ( snd_blocks - BELOW_CHUNKS ) * CHUNK_SAMPLES / RATE
                    sys.stderr.write('%.1f: *** skip too long recording (%.1f)'%(time.time(),dur)+'\n')
                    r = array('h') # clear
                    break

                if silent:
                    num_silent += 1
                    if num_silent >= BELOW_CHUNKS:
                        if __display_dirty: sys.stderr.write('\n')
                        __display_dirty = False
                        #sys.stderr.write('%.1f: [[record:finished]]'%(t_now,)+'\n')

                        if snd_blocks < MIN_CHUNKS: # too short
                            dur = ( snd_blocks - BELOW_CHUNKS ) * CHUNK_SAMPLES / RATE
                            sys.stderr.write('%.1f: *** skip too short recording (%.1f)'%(time.time(),dur)+'\n')
                            r = array('h') # clear

                        break
                else:
                    num_silent = 0

        # prefare snd_frame for next iteration
        snd_frame = array('h')
        snd_frame.extend(snd_chunk)

    stream.stop_stream()
    stream.close()
    p.terminate()

    if len(r) > 0:
        r = normalize(r)
        r = trim(r)
        r = add_silence(r, 0.5)

    #sys.stderr.write('%.1f: [[record:done len=%d]]'%(t_now,len(r),)+'\n')

    return r

def record_to_file(path, wait=True):
    "Records from the microphone and outputs the resulting data to 'path'"
    data = record(wait)

    # recording cancelled?
    if len(data) == 0:
        return False

    # pack as byte array
    data = pack('<' + ('h'*len(data)), *data)

    # sample rate convert 24000 -> 16000
    data,_ = audioop.ratecv(data,2,CHANNELS,RATE,RATE_OUTPUT,None)

    f = open(path,'wb')
    f.write(data)
    f.close()

    return True


# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
