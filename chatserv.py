#!/usr/local/bin/python3
import sys
if __name__ == '__main__':
	#We are the invoked module - but we can't do anything.
	#We aren't actually a module, we're a script. All our variables are accessible only to us.
	#Most other modules will import chatserv, but will end up with the problem that
	#the chatserv they import is not the same as this chatserv - it's the module, not this main script.
	#So instead of doing work that will fall on deaf ears, we import the module chatserv and make it do the work.
	#All working components are then modules - problem solved.
	import chatserv
	chatserv.init()
	sys.exit()

from queue import Queue
import multiprocessing
import json

from util import HTTP
from chat import Chat
#This might be confusing to python people, but it conforms with Torus.
#Luckily, the standard io module is never used. So in this application, io is always coms/io
from coms import io

user = ''
password = ''
session = ''
version = 1

chats = {}
stack = Queue()

class StackEvent():
	def __init__(self, func, args = (), kwargs = {}):
		self.func = func
		self.args = args
		self.kwargs = kwargs

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

def init():
	global user, password
	#FIXME: find a better way of passing username/password than through argv
	if len(sys.argv) < 3: raise Exception('Must specify username and password')
	user = sys.argv[1]
	password = sys.argv[2]
	login()
	Chat(4777) #TODO: possibly use a database to remember rooms to join, settings, etc

	while True:
		event = stack.get()
		try: event.func(*event.args, **event.kwargs)
		#except: print('Failed to handle event', event)
		finally: stack.task_done()
