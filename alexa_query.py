# -*- coding: utf-8 -*-
import sys,time,logging

import requests
import json
import yaml
import re
import uuid

import pprint

from creds import *


#from memcache import Client
#servers = ["127.0.0.1:11211"]
#mc = Client(servers, debug=1)


# 뭘 여기에 memcache 씩이나..
# fakemc_get() fakemc_set() 은 1 item 기억 가능한 memcache 시뮬레이션

class fakemc:

    _key = None
    _value = None
    _expire = 0

    def get(self,key):

        if not key == self._key:
            logging.warn('fakemc_get: wrong key: %s %s',key,self._key)
            return None

        t_now = time.time()
        if t_now >= self._expire:
            hlog.log('fakemc_get: key expired: %.1f %.1f'%(t_now,self._expire,))
            return None

        return self._value

    def set(self,key,value,ttl):
        self._key = key
        self._value = value
        self._expire = time.time() + ttl


mc = fakemc()


class httplog:

    _log_file = None

    def start(self,log_fn):
        self._log_file = open(log_fn,'wb')

    def stop(self,):
        self._log_file.close()
        self._log_file = None

    def log(self,title,**kwargs):
        if self._log_file:
            log = self._log_file
        else:
            log = sys.stderr
        log.write('%.1f: [[%s]]'%(time.time(),title,)+'\n')
        if kwargs:
            yaml.safe_dump(kwargs,log,default_flow_style=False)


hlog = httplog()



def gettoken():

    token = mc.get("access_token")

    if token is not None:
        return token

    refresh = refresh_token # refresh_token from creds.py

    if refresh is not None:

        payload = {"client_id" : Client_ID, "client_secret" : Client_Secret, "refresh_token" : refresh, "grant_type" : "refresh_token", }
        url = "https://api.amazon.com/auth/o2/token"

        sys.stderr.write('%.1f: gettoken: request: url=%s'%(time.time(),url,)+'\n')

        r = requests.post(url, data = payload)
        resp = json.loads(r.text)

        sys.stderr.write('%.1f: gettoken: response: token_len=%d'%(time.time(),len(resp['access_token']),)+'\n')

        token = resp['access_token']

        mc.set("access_token",token,3570)

        return token

    else:

        return False

def internet_on():
    sys.stderr.write('Checking Internet Connection'+'\n')
    try:
        r = requests.get('https://api.amazon.com/auth/o2/token')
        sys.stderr.write('Connection OK'+'\n')
        gettoken()
        return True
    except:
        sys.stderr.write('Connection Failed'+'\n')
        logging.exception("Exception")
        return False

def alexa_query(recording,response,http_log_fn):
    """
    recording: recorded raw file from mic
    response: path where response mp3 from alexa server stored
    """

    hlog.start(http_log_fn)

    url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
    token = gettoken()
    headers = {'Authorization' : 'Bearer %s' % token}
    stream_id = str(uuid.uuid4())
    d = {
       "messageHeader": {
           "deviceContext": [
               {
                   "name": "playbackState",
                   "namespace": "AudioPlayer",
                   "payload": {
                       "streamId": "", #stream_id,
                       "offsetInMilliseconds": "0",
                       "playerActivity": "IDLE"
                   }
               }
           ]
        },
       "messageBody": {
           "profile": "alexa-close-talk",
           "locale": "en-us",
           "format": "audio/L16; rate=16000; channels=1"
       }
    }
    with open(recording,'rb') as inf:
        files = [
                ('file', ('request', json.dumps(d), 'application/json; charset=UTF-8')),
                ('file', ('audio', inf, 'audio/L16; rate=16000; channels=1'))
                ]

        t_now = time.time()
        hlog.log('alexa_query:request',url=url,headers=headers,request=d)

        r = requests.post(url, headers=headers, files=files)

        t_now = time.time()
        hlog.log('alexa_query:response',status=r.status_code)

        sys.stderr.write('%.1f: http: status: %d'%(time.time(),r.status_code,)+'\n')

        if r.status_code == 200:

            #hlog.log('alexa:response',headers=r.headers)
            pprint.pprint('%.1f: [[alexa:response]]'%(time.time(),),hlog._log_file)
            pprint.pprint(r.headers,hlog._log_file)

            for v in r.headers['content-type'].split(";"):
                if re.match('.*boundary.*', v):
                    boundary =  v.split("=")[1]
            data = r.content.split(boundary)
            for d in data:
                if len(d) > 2:
                    part = d.split('\r\n\r\n') # '' for first split, '--' for last split
                    if len(part) >= 2:
                        part_header = part[0][2:]
                        hlog.log('part-header',headers=part_header[:min(len(part_header),200)])
                        part_body = part[1].rstrip('--')
                        # Content-Type: application/json
                        # Content-Type: audio/mpeg
                        if part_header.find('Content-Type: application/json') > -1:
                            payload = json.loads(part_body)
                            hlog.log('part-json',length=len(part_body),payload=payload)
                            try:
                                desc=payload['messageBody']['directives'][0]['payload']['audioContent']
                                sys.stderr.write('%.1f: http: %s'%(time.time(),desc,)+'\n')
                            except:
                                logging.exception("Exception")
                        if part_header.find('Content-Type: audio/') > -1:
                            hlog.log('part-audio',length=len(part_body))
                            audio = part_body
                            try:
                                with open(response, 'wb') as f: f.write(audio)
                            except:
                                logging.exception("Exception")
        else:
            pprint.pprint(r,hlog._log_file)


    hlog.stop()


# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
