#
import os,sys,time
import pygame

#EXTERNAL_MP3_PLAYER=None
EXTERNAL_MP3_PLAYER="mpg123 -q -m -r 24000"

#pygame.mixer.init(frequency=24000,size=-16,channels=1)
pygame.mixer.init(frequency=24000,size=-16,channels=1,buffer=720)

path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))

sound_chan = None
sound_cache = {}

def play_sound(fn,timeout_millis=-1):

    global sound_chan,sound_cache

    def log(msg,*args):
        sys.stderr.write(('%.1f: '%(time.time(),))+(msg % args)+'\n')

    if not sound_chan:
        log('play_sound: create channel')
        sound_chan = pygame.mixer.find_channel()

    if not fn in sound_cache:
        log('play_sound: create new sound %s',os.path.basename(fn))
        snd_obj = pygame.mixer.Sound(fn)
        sound_cache[fn] = snd_obj

    sound = sound_cache[fn]

    clock = pygame.time.Clock()
    tstart = pygame.time.get_ticks()

    log('play_sound: start %s',os.path.basename(fn))

    ch = sound_chan
    ch.play(sound)

    while ch.get_busy():
        telapsed = pygame.time.get_ticks() - tstart
        if timeout_millis >= 0 and telapsed > timeout_millis:
            break
        clock.tick(10)

    #log('play_sound: end %s elapsed=%.1f',fn,telapsed)

    ch.stop()

def play_music(fn,timeout_millis=-1):

    def log(msg,*args):
        sys.stderr.write(('%.1f: '%(time.time(),))+(msg % args)+'\n')

    if EXTERNAL_MP3_PLAYER:
        os.system('%s %s'%(EXTERNAL_MP3_PLAYER,fn))
    else:
        clock = pygame.time.Clock()
        tstart = pygame.time.get_ticks()

        log('play_music: start %s',os.path.basename(fn))

        pygame.mixer.music.load(fn)
        pygame.mixer.music.play(loops=0,start=0.0)

        while pygame.mixer.music.get_busy():
            telapsed = pygame.time.get_ticks() - tstart
            if timeout_millis >= 0 and telapsed > timeout_millis:
                break
            clock.tick(10)

        #log('play_music: end %s telapsed=%.1f',fn,telapsed)

        pygame.mixer.music.stop()

# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
