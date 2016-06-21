:
pm2 start --watch .  --ignore-watch sounds --ignore-watch etc /opt/sam-alexa-pi/main.py
exec tail -F ~/.pm2/logs/main-out-[0-9].log -F ~/.pm2/logs/main-error-[0-9].log -F /tmp/mpd.log # -F /dev/shm/alexa-pi/http.log
