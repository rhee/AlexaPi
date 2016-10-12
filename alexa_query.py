# -*- coding: utf-8 -*-
import sys,time,logging

import requests
from requests_toolbelt.multipart import decoder
import json
import yaml
import re
import uuid

import pprint

from creds import *


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
            try:
                yaml.safe_dump(kwargs,log,default_flow_style=False)
            except:
                log.write('=')
                pprint.pprint(kwargs,log)

hlog = httplog()



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

def alexa_query(raw,response,http_log_fn):
    """
    recording: recorded raw file from mic
    response: path where response mp3 from alexa server stored
    """

    hlog.start(http_log_fn)

    directives = {}

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

    files = [
            ('file', ('request', json.dumps(d), 'application/json; charset=UTF-8')),
            ('file', ('audio', raw, 'audio/L16; rate=16000; channels=1'))
            ]

    hlog.log('alexa_query:request',url=url,headers=headers,request=d)

    r = requests.post(url, headers=headers, files=files)

    hlog.log('alexa_query:response:status',status=r.status_code)

    sys.stderr.write('%.1f: http: status: %d'%(time.time(),r.status_code,)+'\n')

    if r.status_code == 200:

        ### CaseInsensitiveDict 를 yaml.safe_dump 할 수 없어서
        ### .items() 를 가지고 새로 dict() 만든다
        hlog.log('alexa_query:response:headers',headers=dict(r.headers.items()))

        multipart_data = decoder.MultipartDecoder.from_response(r)

        for part in multipart_data.parts:
            hlog.log('part-header',headers=dict(part.headers.items()))
            # Content-Type: application/json
            # Content-Type: audio/mpeg
            if part.headers['content-type'] == 'application/json':
                payload = json.loads(part.content)
                hlog.log('part-json',length=len(part.content),payload=payload)
                try:
                    for directive in payload['messageBody']['directives']:
                        if directive['name'] == 'speak':
                            desc=directive['payload']['audioContent']
                            sys.stderr.write('%.1f: http: %s %s'%(time.time(),directive['name'],desc,)+'\n')
                        else:
                            sys.stderr.write('%.1f: http: %s'%(time.time(),directive['name'],)+'\n')
                        directives[directive['name']] = directive
                except:
                    logging.exception("Exception")
                    hlog.log('dump of part-json',payload=payload)
            if part.headers['content-type'].startswith('audio/'):
                hlog.log('part-audio',length=len(part.content))
                audio = part.content
                try:
                    with open(response, 'wb') as f: f.write(audio)
                except:
                    logging.exception("Exception")

    else:
        pprint.pprint(r,hlog._log_file)

    hlog.stop()

    return directives


# Emacs:
# mode: javascript
# c-basic-offset: 4
# tab-width: 8
# indent-tabs-mode: nil
# End:
# vim: se ft=javascript st=4 ts=8 sts=4
