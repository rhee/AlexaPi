#!/bin/sh
#mpd --no-config --no-daemon --stderr mpd.conf
mpd --no-daemon --stderr mpd.conf 2>/dev/shm/alexa-pi/mpd.log &
