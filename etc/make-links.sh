:
mkdir -p /tmp/r

for d in /tmp/r/*; do
  if [ -e $d ]; then
    # try remove os-x sshfs mount, linux sshfs mount, mountpoint, symbolic link, in turn
    \fusermount -u $d 2>/dev/null
    \umount $d 2>/dev/null
    \rmdir $d 2>/dev/null
    \rm $d 2>/dev/null
  fi
done

if [ -d /Users/rhee/Downloads/dbox/Dropbox/alexa-pi-demo/data ]; then
  ln -s /Users/rhee/Downloads/dbox/Dropbox/alexa-pi-demo/data /tmp/r/data
else
  mkdir /tmp/r/data
  sshfs mini2.local:Downloads/dbox/Dropbox/alexa-pi-demo/data /tmp/r/data
fi

if [ -d /Users/rhee/R/voice-recog ]; then
  ln -s /Users/rhee/R/voice-recog /tmp/r/tools
else
  mkdir /tmp/r/tools
  sshfs mini2.local:R/voice-recog /tmp/r/tools
fi

if [ -d /home/pi/Build/alexa-pi-demo/AlexaPi ]; then
  ln -s /home/pi/Build/alexa-pi-demo/AlexaPi /tmp/r/alexapi
else
  mkdir /tmp/r/alexapi
  sshfs rpi3.local:/home/pi/Build/alexa-pi-demo/AlexaPi /tmp/r/alexapi
fi

if [ -d /Users/rhee/R/secrets ]; then
  ln -s /Users/rhee/R/secrets /tmp/r/secrets
fi

if [ -d /home/rhee/R/secrets ]; then
  ln -s /home/rhee/R/secrets /tmp/r/secrets
fi
