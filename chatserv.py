#!/usr/local/bin/python3
import os, sys
from threading import Thread, Lock
import multiprocessing
import json

import util.HTTP as HTTP
import api 

user = ''
password = ''
session = ''
version = 1

chats = []

def test():
	data = api.spider('community')
	print(api.session(2087, data['chatkey'], data['nodeHostname'], data['nodePort']))

def open(room, key = None, server = None, port = None, session = None, transport = None):
	#FIXME: is this function actually necessary?
	return Chat(room, key, server, port, session, transport)

class Chat(Thread):
	def __init__(self, room, key = None, server = None, port = None, session = None, transport = None):
		global chats
		if self.room <= 0: raise Exception('Invalid room id') #TODO: ConnectionError
		Thread.__init__(self, name='chat-' + room)

		self.id = room
		self.key = key
		self.server = server
		self.port = port
		self.session = session
		self.transport = transport

		self.connected = False
		self.connecting = True
		self.reconnecting = False
		self.userlist = {}

		chats[self.room] = self
		self.start()
	def run(self):
		if self.key == None || self.server == None:
			#FIXME: this will always make the server chat2-2, which would make connecting to
			#halo or runescape impossible by room id. Not that you'd ever have to, but it would.
			#most domains are on chat2-2 though, so this should at least accidentally not break most wikis.
			data = api.spider('community')
			if 'exception' in data: raise Exception(data['exception']['message']) #wiki doesn't have chat, probably
			else if not isinstance(data['chatkey']): raise Exception('Chatkey is false')
			if self.key == None: self.key = data['chatkey']
			if self.server == None: self.server = data['nodeHostname']
			if self.port == None: self.port = data['nodePort']
		if self.port == None: self.port = 80 #it's not worth wasting time making an HTTP request when it's just going to be 80
		if self.session == None: self.session = api.session(self.room, self.key, self.server, self.port)
		if self.transport == None: self.transport = 'xhr-polling' #this will be important if websockets are ever allowed again
		self.socket = api.transports[self.transport](self.room, self.key, self.server, self.port, self.session)
		self.socket.connect()

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
