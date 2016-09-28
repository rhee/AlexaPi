import sys

if sys.platform.startswith('linux'):
    if sys._multiarch == 'arm-linux-gnueabihf':
        from rpi import snowboydecoder
    else:
        from linux import snowboydecoder

if sys.platform.startswith('darwin'):
    from osx import snowboydecoder

