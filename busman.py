#! /usr/bin/env python
# -*- coding: utf-8 -*-

from traceback import print_exc
import logging
import json
import re
import requests
import pymysql as MySQLdb

from creds import WIT_AI_TOKEN

def lookup_bus_number(conn, context, query_text):
    try:
        m = re.match(r'([0-9-]{1-5})번', query_text)
    except:
        logging.exception("re.match")
    pass

def lookup_bus_station(conn, context, query_text):
    pass

def lookup_bus_station_hint(conn, context, query_text):
    pass

def query_bus_arrival(conn, context):
    pass

def get_bus_arrival(context, query_text):
    
    with MySQLdb.connect(
        host='172.30.1.110', 
        port=13306, 
        user='busman', 
        password='busman-chat-user-1447',
        db='busman', 
        charset='utf8mb4') as conn:

        lookup_bus_number(conn, context, query_text)
        if not 'bus_number' in context:
            context['response'] = '버스 번호를 알려 주세요'
            return

        lookup_bus_station(conn, context, query_text)
        if not 'bus_station' in context:
            context['response'] = '버스 정류장을 알려 주세요'
            return

        lookup_bus_station_hint(conn, context, query_text)

        query_bus_arrival(conn, context)
        
        if 'bus_arrival' in context:
            pass
            
        if 'multiple_bus_arrivals' in context:
            pass
            
    context['response'] = '버스 번호나 버스 정류장을 찾지 못했습니다'
    return


############################
    
context = dict()

def busman_query(mic):
    
    def gen():
        while True:
            chunk = mic.read()
            yield chunk
            if len(chunk) == 0:
                break

    headers = {
        'Authorization': 'Bearer '+WIT_AI_TOKEN,
        'Content-Type': 'audio/raw;encoding=signed-integer;bits=16;rate=16000;endian=little'
        }
    url = "https://api.wit.ai/speech?v=20160526"
    r = requests.post(
        url, #url + '?' + urllib.urlencode(payload),
        data = gen(),
        headers = headers)

    # response example:
    # {
    # "msg_id" : "15cce324-4395-437a-ae1f-76b19666b2e4",
    # "_text" : "360번 버스",
    # "entities" : { }
    # }

    #sys.stderr.write('response: '+r.text.encode('utf-8')+'\n')
    logging.info('response: '+r.text.encode('utf-8')+'\n')

    resp = json.loads(r.text)
    get_bus_arrival(context, resp['_text'])
    
    #sys.stderr.write('get_bus_arrival: '+json.dumps(context)+"\n")
    logging.info('get_bus_arrival: '+json.dumps(context)+"\n")
    
    sys.stdout.write(context['response'] + "\n")
    
    return { "response" : context['response'] }
