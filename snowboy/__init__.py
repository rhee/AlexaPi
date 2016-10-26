import sys

if sys.platform.startswith('linux'):
    if sys._multiarch == 'arm-linux-gnueabihf':
        print 'arm-linux-gnueabihf detected'
        # try import rpi3 version
        try:
            from rpi import snowboydecoder
        except:
            # try tk1 version, if rpi3 version fails
            from tk1 import snowboydecoder
    else:
        from linux import snowboydecoder

if sys.platform.startswith('darwin'):
    from osx import snowboydecoder

