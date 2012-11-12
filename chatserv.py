#!/usr/local/bin/python3
import sys
if __name__ == '__main__':
	#We are the invoked module - but we can't do anything.
	#We aren't actually a module, we're a script. All our variables are accessible only to us.
	#Most other modules will import chatserv, but will end up with the problem that
	#the chatserv they import is not the same as this chatserv - they import the module, not this main script.
	#So instead of doing work that will fall on deaf ears, we import the module chatserv and make it do the work.
	#All working components are then modules - problem solved.
	if len(sys.argv) < 3: raise Exception('Must specify username and password')
	import chatserv
	chatserv.init(sys.argv[1], sys.argv[2])
	sys.exit()

import json

from util import HTTP
#This might be confusing to python people, but it conforms with Torus.
#This should only ever be referred to as chatserv.io, never directly imported by another module.
import inout as io
from stack import *
from chats import *
import users.temp, users.persist
import commands

user = ''
password = ''
session = ''
version = 1

def open(room, key = None, server = None, port = None, session = None, transport = None):
	#FIXME: is this function actually necessary?
	return Chat(room, key, server, port, session, transport)

def logout():
	print('Closing...')
	for i in dict(chats):
		chats[i].sendCommand('logout')
		chats[i].kill()

def login(name = None, passw = None):
	global session, user, password
	if name == None: name = user
	if passw == None: passw = password
	print('Logging in...')
	response = HTTP.post('http://community.wikia.com/api.php', {'action': 'login', 'lgname': name, 'lgpassword': passw, 'format': 'json'})
	cookie = response.getheader('Set-Cookie')
	newsession = cookie[:cookie.find(';') + 1]

	result = json.loads(response.read().decode('utf-8'))
	try: HTTP.post('http://community.wikia.com/api.php', {'action': 'login', 'lgname': name, 'lgpassword': passw, 'lgtoken': result['login']['token']}, {'Cookie': newsession})
	except:
		print(result)
		raise
	user = name #this should minimize race conditions if we ever have to log in again while connected
	password = passw
	session = newsession
	print('Session:', session)

def isloggedin():
	return bool(json.loads(HTTP.get('http://community.wikia.com/api.php', {'action': 'query', 'meta': 'userinfo', 'format': 'json'}, {'Cookie': session}).read().decode('utf-8')))

def init(name, passw):
	global user, password
	user = name
	password = passw
	login()
	Chat('monchbox') #TODO: possibly use a database to remember rooms to join, settings, etc

	while True:
		event = stack.get()
		try:
			if event.type == 'context': event()
			else: raise Exception('Unrecognized event type ' + event.type)
		except Exception:
			logout()
			raise
			sys.exit()
		finally: stack.task_done()

