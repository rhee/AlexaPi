#
import sys,time
import types
import math

import pyaudio
import audioop

from sys import byteorder
from array import array
from struct import pack

import numpy as np




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

def normalize(snd_chunk):
    "Average the volume out"
    
    times = float(NORMALIZE_LEVEL)/max(abs(i) for i in snd_chunk)
    r = array('h')
    for i in snd_chunk:
        r.append(int(i*times))
    return r

def trim(snd_chunk, threshold):
    "Trim the blank spots at the start and end"

    def _trim(snd_chunk):
        snd_started = False
        r = array('h')
        for i in snd_chunk:
            if not snd_started and abs(i)>threshold:
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


class prowneddict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)


class microphone:

    def __init__(self, wait):
        self.rms = THRESHOLD_INITIAL_BASE
        self.rms_max = self.rms_min = self.rms
        self.threshold = self.rms + THRESHOLD_MARGIN
        self.display_time = time.time()
        self.display_dirty = False

        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, output=True,
                        frames_per_buffer=CHUNK_SAMPLES)

        # FIXME: nonlocal num_silent, num_noisy, num_chunks, recording, test_chunk

        st = prowneddict() # recording state: poorman's nonlocal
        st.num_silent = 0
        st.num_noisy = 0
        st.num_chunks = 0
        st.recording = array('h')
        st.test_chunk = array('h') # chunk to analyze ( 2 * CHUNK_SAMPLES samples )
        st.ratecv_state = None
        st.eof = False

        def _read(self, numbytes=-1):
            # FIXME: nonlocal num_silent, num_noisy, num_chunks, recording, test_chunk
            
            def _read_buf(st, numbytes):
                # # pack as byte array
                # this_chunk = pack('<' + ('h'*len(this_chunk)), *this_chunk)
                if numbytes < 0:
                    numbytes = len(st.recording)
                numwords = numbytes / 2
                result = array('h', st.recording[:numwords])
                st.recording = st.recording[numwords:]
                return pack('<' + ('h' * numwords), *result)

            if st.eof:
                raise IOError('read() after EOF')

            while True:
                
                # little endian, signed short
                this_chunk = array('h', stream.read(CHUNK_SAMPLES, exception_on_overflow=False))

                #sys.stderr.write('mic.read: got ' + str(len(this_chunk)) + ' samples' + '\n')

                if (len(this_chunk) == 0):
                    st.test_chunk = array('h') # empty test_chunk
                    sys.stderr.write('mic.read: return empty' + '\n')
                    return array('h') # no input

                if byteorder == 'big':
                    this_chunk.byteswap()

                st.test_chunk.extend(this_chunk)    # make test_chunk + this_chunk
                silent = self.is_silent(st.test_chunk)

                self.adjust_threshold()
                self.update_status(st.num_chunks)

                if 0 == st.num_chunks: # check recording start condition

                    if wait and silent:
                        st.num_noisy = 0
                        st.recording = array('h') # truncate buffer
                    else:
                        st.num_noisy += 1
                        if st.num_noisy >= ABOVE_CHUNKS:
                            self.clear_status()
                            st.num_chunks = 1

                else: # check recording stop condition

                    st.num_chunks += 1

                    if st.num_chunks > MAX_CHUNKS + BELOW_CHUNKS: # ignore if the sample longer than 9.5s
                        self.clear_status()
                        dur = ( st.num_chunks - BELOW_CHUNKS ) * CHUNK_SAMPLES / RATE
                        sys.stderr.write('%.1f: *** skip too long recording (%.1f)'%(time.time(),dur)+'\n')
                        st.eof = True
                        sys.stderr.write('mic.read: too-long: return empty' + '\n')
                        return _read_buf(st, numbytes) # return samples read so far

                    if silent:
                        st.num_silent += 1
                        if st.num_silent >= BELOW_CHUNKS:
                            self.clear_status()
                            if st.num_chunks < MIN_CHUNKS: # too short
                                dur = ( st.num_chunks - BELOW_CHUNKS ) * CHUNK_SAMPLES / RATE
                                sys.stderr.write('%.1f: *** skip too short recording (%.1f)'%(time.time(),dur)+'\n')
                                st.eof = True
                                sys.stderr.write('mic.read: short: return empty' + '\n')
                            return _read_buf(st, numbytes) # return samples read so far
                    else:
                        st.num_silent = 0

                # prefare test_chunk for next iteration
                st.test_chunk = array('h')
                st.test_chunk.extend(this_chunk)

                # sample rate convert 24000 -> 16000
                new_chunk,st.ratecv_state = audioop.ratecv(this_chunk,2,CHANNELS,RATE,RATE_OUTPUT,st.ratecv_state)

                st.recording.extend(array('h',new_chunk)) # NOTE: audioop.ratecv() returns (str,state)
                
                # enough?
                if numbytes > -1 and 2 * len(st.recording) >= numbytes:
                    break
                
            sys.stderr.write('mic.read: return response: ' + str(numbytes) + '\n')
            return _read_buf(st, numbytes)


        def _close(self):
            stream.stop_stream()
            stream.close()
            audio.terminate()


        self.read = types.MethodType(_read, self) #_read
        self.close = types.MethodType(_close, self) #_read

    # run for each chunk, ( 1/100s )
    def adjust_threshold(self):
        "update threshold"
        
        # adjust current threshold. to follow-up th_target, within 3000 chunks, ( 30s )
        th_target = self.rms + THRESHOLD_MARGIN
        th_delta = th_target - self.threshold
        self.threshold += th_delta / 100.0 / 30.0
        self.rms_max = max(self.rms_max,self.rms)
        self.rms_min = min(self.rms_min,self.rms)


    def is_silent(self,snd_chunk):
        "Returns 'True' if below the 'silent' threshold"
        
        self.rms = current = audioop.rms(snd_chunk,2)
        return current < self.threshold


    def clear_status(self):
        if self.display_dirty: sys.stderr.write('\n')
        self.display_dirty = False


    def update_status(self, num_chunks):
        # show status at interval 1s
        t_now = time.time()
        if t_now >= self.display_time + 0.5:
            if 0 == num_chunks:
                print_vumeter(False, self.rms_min,self.rms_max,self.threshold)
            else:
                print_vumeter(True, self.rms_min,self.rms_max,self.threshold, ('recording: %5.1f %5.1f' % ( min(0,num_chunks/1000.0-1.0), num_chunks/100.0,)))
            self.rms_max = self.rms_min = self.rms
            self.display_time = t_now
            self.display_dirty = True


    def readLine(self, n=-1):
        raise IOError('readLine() not supported for microphone')
        

    def write(str):
        raise IOError('write() not supported for microphone')


# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
