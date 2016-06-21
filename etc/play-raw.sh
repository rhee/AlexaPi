#!/bin/sh
# play 16000r, 1ch, 16-bit signed raw data
exec play -b 16 -c 1 -r 16000 -e signed "$@"
