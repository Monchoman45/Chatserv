#!/usr/local/bin/python3
import os, sys
import multiprocessing
import json

from util import HTTP
from chat import Chat
import api

user = ''
password = ''
session = ''
version = 1

chats = {}

def test():
	Chat(4777)

def open(room, key = None, server = None, port = None, session = None, transport = None):
	#FIXME: is this function actually necessary?
	return Chat(room, key, server, port, session, transport)

def login(name = None, passw = None):
	global session, user, password
	if name == None: name = user
	if passw == None: passw = password
	print('Logging in...')
	response = HTTP.post('http://community.wikia.com/api.php', {'action': 'login', 'lgname': name, 'lgpassword': passw, 'format': 'json'})
	cookie = response.getheader('Set-Cookie')
	newsession = cookie[:cookie.find(';') + 1]

	HTTP.post('http://community.wikia.com/api.php', {'action': 'login', 'lgname': name, 'lgpassword': passw, 'lgtoken': json.loads(response.read().decode('utf-8'))['login']['token']}, {'Cookie': newsession})
	user = name #this should minimize race conditions if we ever have to login in again while connected
	password = passw
	session = newsession
	print('Session:', session)

def loggedin():
	return bool(json.loads(HTTP.get('http://community.wikia.com/api.php', {'action': 'query', 'meta': 'userinfo', 'format': 'json'}, {'Cookie': session}).read().decode('utf-8')))

#FIXME: find a better way of passing username/password than through argv
if len(sys.argv) < 3: raise Exception('Must specify username and password')
user = sys.argv[1]
password = sys.argv[2]
login()
test()
