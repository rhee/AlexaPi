#
import sys,time
import math

import pyaudio
import audioop

from sys import byteorder
from array import array
from struct import pack




ABOVE_DURATION = 20      # 0.2s
BELOW_DURATION = 150     # 1.5s

MIN_DURATION = 150       # 1.5s
MAX_DURATION = 950       # 9.5s


NORMALIZE_LEVEL = 16384  # 50% of max amp
THRESHOLD_INITIAL_BASE = 0
THRESHOLD_MARGIN = 819  # 1638 ~ 32768 * 0.05, 819 ~ 32768 * 0.025


CHANNELS = 1
FORMAT = pyaudio.paInt16
RATE = 16000
REC_CHUNK_SIZE = 160     # 0.01s approx


# class color:
#     black   = '\033[1;37;40m'
#     red     = '\033[1;37;41m'
#     green   = '\033[1;37;42m'
#     yellow  = '\033[1;37;43m'
#     blue    = '\033[1;37;44m'
#     magenta = '\033[1;37;45m'
#     cyan    = '\033[1;37;46m'
#     white   = '\033[1;37;47m'
#     nocolor = '\033[0m'


#range0  = color.white
#range1  = color.green
#range2  = color.red
#range3  = color.yellow

range0  = '\033[1;37;42m'
range1  = '\033[1;30;42m'
range2  = '\033[1;31;43m'
range3  = '\033[1;37;43m'
nocolor = '\033[0m'


__current_rms = THRESHOLD_INITIAL_BASE
__current_rms_max = __current_rms_min = __current_rms
__current_threshold = __current_rms + THRESHOLD_MARGIN
__display_time = time.time()
__display_dirty = False

def is_silent(snd_data):
    "Returns 'True' if below the 'silent' threshold"

    global __current_rms

    __current_rms = current = audioop.rms(snd_data,2)
    return current < __current_threshold

def print_vumeter(fmin,fmax,fthr):
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
    sys.stderr.write('[ %s ] %6d %6d' % ( s, fmin, fthr, ) + '\r')


# run for each chunk, ( 1/100s )
def adjust_threshold(rec_blocks):
    "update threshold"

    global __display_time,__current_threshold,__current_rms_max,__current_rms_min,__display_dirty

    # adjust current threshold. to follow-up th_target, within 3000 chunks, ( 30s )
    th_target = __current_rms + THRESHOLD_MARGIN
    th_delta = th_target - __current_threshold

    __current_threshold += th_delta / 100.0 / 30.0
    __current_rms_max = max(__current_rms_max,__current_rms)
    __current_rms_min = min(__current_rms_min,__current_rms)

    # show status at interval 1s
    t_now = time.time()

    if t_now >= __display_time + 0.5:
        if 0 == rec_blocks:
            print_vumeter(__current_rms_min,__current_rms_max,__current_threshold)
        else:
            sys.stderr.write('%.1f: [[recording: %5.1f]]' % ( t_now, rec_blocks/100.0, ) + '\r')
        __display_time = t_now
        __current_rms_max = __current_rms_min = __current_rms
        __display_dirty = True

def normalize(snd_data):
    "Average the volume out"
    times = float(NORMALIZE_LEVEL)/max(abs(i) for i in snd_data)
    r = array('h')
    for i in snd_data:
        r.append(int(i*times))
    return r

def trim(snd_data):
    "Trim the blank spots at the start and end"

    def _trim(snd_data):
        snd_started = False
        r = array('h')

        for i in snd_data:
            if not snd_started and abs(i)>__current_threshold:
                snd_started = True
                r.append(i)

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data)
    snd_data.reverse()
    return snd_data

def add_silence(snd_data, seconds):
    "Add silence to the start and end of 'snd_data' of length 'seconds' (float)"
    r = array('h', [0 for i in xrange(int(seconds*RATE))])
    r.extend(snd_data)
    r.extend([0 for i in xrange(int(seconds*RATE))])
    return r

def record():
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
                    frames_per_buffer=REC_CHUNK_SIZE)

    t_now = time.time()
    #sys.stderr.write('%.1f: [[record:listening...]]'%(t_now,)+'\n')

    num_silent = 0
    num_noisy = 0
    snd_blocks = 0

    r = array('h')

    while 1:

        t_now = time.time()

        # little endian, signed short
        snd_data = array('h', stream.read(REC_CHUNK_SIZE))

        if byteorder == 'big':
            snd_data.byteswap()

        r.extend(snd_data)

        silent = is_silent(snd_data)

        if 0 == snd_blocks: # check recording start condition

            if silent:
                num_noisy = 0
                r = array('h') # truncate buffer
            else:
                num_noisy += 1
                if num_noisy >= ABOVE_DURATION:
                    if __display_dirty: sys.stderr.write('\n')
                    __display_dirty = False
                    #sys.stderr.write('%.1f: [[record:started]]'%(t_now,)+'\n')
                    snd_blocks = 1

        else: # check recording stop condition

            snd_blocks += 1

            if snd_blocks > MAX_DURATION: # ignore if the sample longer than 9.5s
                if __display_dirty: sys.stderr.write('\n')
                __display_dirty = False
                #sys.stderr.write('%.1f: [[record:cancelled]]'%(t_now,)+'\n')
                r = array('h') # clear
                break

            if silent:
                num_silent += 1
                if num_silent >= BELOW_DURATION:
                    if __display_dirty: sys.stderr.write('\n')
                    __display_dirty = False
                    #sys.stderr.write('%.1f: [[record:finished]]'%(t_now,)+'\n')
                    break
            else:
                num_silent = 0

        adjust_threshold(snd_blocks)

    stream.stop_stream()
    stream.close()
    p.terminate()

    if len(r) > 0:
        r = normalize(r)
        r = trim(r)
        r = add_silence(r, 0.5)

    #sys.stderr.write('%.1f: [[record:done len=%d]]'%(t_now,len(r),)+'\n')

    return r

def record_to_file(path):
    "Records from the microphone and outputs the resulting data to 'path'"
    data = record()

    if data is None or len(data) == 0:
        sys.stderr.write('%.1f: *** no recording (%.1f)'%(time.time(),0.0)+'\n')
        return

    blocks = len(data) / 2 / 100
    dur = len(data) / 2.0 / 16000.0

    if blocks < MIN_DURATION: # too short
        #sys.stderr.write('%.1f: [[record: skip short/cancelled data]]'%(time.time(),)+'\n')
        sys.stderr.write('%.1f: *** skip too short recording (%.1f)'%(time.time(),dur)+'\n')
        return

    if blocks > MAX_DURATION: # too long
        #sys.stderr.write('%.1f: [[record: skip data too long]]'%(time.time(),)+'\n')
        sys.stderr.write('%.1f: *** skip too long recording (%.1f)'%(time.time(),dur)+'\n')
        return

    sys.stderr.write('%.1f: recorded %.1f'%(time.time(),dur)+'\n')

    data = pack('<' + ('h'*len(data)), *data)
    f = open(path,'wb')
    f.write(data)
    f.close()

# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
