#!/bin/sh -e

# example from sox.1
#
# play -n -c1 synth sin %-12 sin %-9 sin %-5 sin %-2 fade h 0.1 1 0.1
# play "|sox -n -p synth 2" "|sox -n -p synth 2 tremolo 10" stat
# play -n synth 2.5 sin 667 gain 1 bend .35,180,.25  .15,740,.53  0,-520,.3
# play -n synth 5 sin %0 50
# play -n synth -j 3 sin %3 sin %-2 sin %-5 sin %-9 sin %-14 sin %-21 fade h .01 2 1.5 delay 1.3 1 .76 .54 .27 remix - fade h 0 2.7 2.5 norm -1
# play -n synth pl G2 pl B2 pl D3 pl G3 pl D4 pl G4 delay 0 .05 .1 .15 .2 .25 remix - fade 0 4 .1 norm -1
# play -n synth 6 tri 10k:14k
# play "|sox -n -p synth 1 sin %1" "|sox -n -p synth 1 sin %3"
# play -n synth 3 sine 300-3300



# sampling rate 24000, ch 1, 16-bit signed, level 0.15

# s1 : 0 x 0.75, 1108.7 x 0.115, 0 x 0.005, 1108.7 x 0.115, 0 x 0.005
# s2 : 0 x 0.75, 830.61 x 0.115, 0 x 0.005, 830.61 x 0.115, 0 x 0.005
# s3 : 0 x 0.75, 440.0 x 0.125, 0 x 0.025, 440.0 x 0.125, 0 x 0.025

#play -n -c1 -b16 -r24000 pad 0.75 synth 0.115 sin 1180.7 pad 0.005 synth 0.115 sin 1180.7 pad 0.005

#play -n -c1 -b16 -r24000 \
#    "|sox -n -p synth 0.115 sin 1180.7 |sox - -p pad 0.75 0.115" \
#    "|sox -n -p synth 0.115 sin 1180.7 |sox - -p pad 0 0.115" \

#play -v 0.15 -n -c1 -b16 -r24000 synth 0.230 sin 1180.7 pad 0.75 0.005@0.115 0.115
#play -v 0.15 -n -c1 -b16 -r24000 synth 0.230 sin 830.61 pad 0.75 0.005@0.115 0.115
#play -v 0.15 -n -c1 -b16 -r24000 synth 0.375 sin 440.0 pad 0.75 0.25@0.125 0.25@0.250 

# sox [gopts] [[fopts] infile]... [fopts] outfile [effect [effopt]]...
# gopts: -v 0.15 
# infile: -n
# fopts: -c1 -b16 -r24000
# outfile: chime1.wav
# effects: synth...

sox -v 0.15 -n -c1 -b16 -r24000 chime1.wav synth 0.230 sin 1180.7 pad 0.25 0.005@0.115 vol 0.15
sox -v 0.15 -n -c1 -b16 -r24000 chime2.wav synth 0.230 sin 830.61 pad 0.25 0.005@0.115 vol 0.15
sox -v 0.15 -n -c1 -b16 -r24000 chime3.wav synth 0.375 sin 440.0 pad 0.25 0.25@0.125 0.25@0.250 vol 0.15

lame chime1.wav chime1.mp3
lame chime2.wav chime2.mp3
lame chime3.wav chime3.mp3
