#!/usr/local/bin/python3
import sys
if __name__ == '__main__':
	#We are the invoked module - but we can't do anything.
	#We aren't actually a module, we're a script. All our variables are accessible only to us.
	#Most other modules will import chatserv, but will end up with the problem that
	#the chatserv they import is not the same as this chatserv - it's the module, not this main script.
	#So instead of doing work that will fall on deaf ears, we import the module chatserv and make it do the work.
	#All working components are then modules - problem solved.
	if len(sys.argv) < 3: raise Exception('Must specify username and password')
	import chatserv
	chatserv.init(sys.argv[1], sys.argv[2])
	sys.exit()

import json

from util import HTTP
from chats import *
#This might be confusing to python people, but it conforms with Torus.
#Luckily, the standard io module is never used. So in this application, io is always coms/io
from coms import io
from stack import *

user = ''
password = ''
session = ''
version = 1

def open(room, key = None, server = None, port = None, session = None, transport = None):
	#FIXME: is this function actually necessary?
	return Chat(room, key, server, port, session, transport)

def logout():
	print('Closing...')
	for i in chats:
		chats[i].sendCommand('logout')
		chats[i].kill()
	sys.exit()

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
		sys.exit()
	user = name #this should minimize race conditions if we ever have to login in again while connected
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
			if event.type == 'call': event.run()
			else: raise Exception('Unrecognized event type ' + event.type)
		except:
			logout()	
			raise
		finally: stack.task_done()

