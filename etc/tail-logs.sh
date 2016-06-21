:
#exec tail -F ~/.pm2/logs/main-out-[0-9].log -F ~/.pm2/logs/main-error-[0-9].log -F /var/log/mpd/mpd.log # -F /dev/shm/alexa-pi/http.log 
exec tail -F ~/.pm2/logs/main-out-[0-9].log -F ~/.pm2/logs/main-error-[0-9].log # -F /var/log/mpd/mpd.log # -F /dev/shm/alexa-pi/http.log 
